"""The app stack: own IAM roles, logs, the two ECS services, the load balancer (CloudFront only) and CloudFront."""
import json

import pytest

from conftest import cfn_lint, load_template, name_properties, resources, sub_text

ORIGIN_VERIFY = {"Fn::Select": [2, {"Fn::Split": ["/", {"Ref": "AWS::StackId"}]}]}  # stable per stack, unguessable
USE_ORIGIN_CACHE_CONTROL = "83da9c7e-98b4-4e11-a168-04f0df8e2c65"  # managed: UseOriginCacheControlHeaders
ALL_VIEWER_EXCEPT_HOST = "b689b0a8-53d0-40ab-baf2-68738e2966ac"  # managed: AllViewerExceptHostHeader
CACHING_OPTIMIZED = "658327ea-f89d-4fab-a63d-7e88639e58f6"  # managed: CachingOptimized


@pytest.fixture(scope="module")
def t():
    return load_template("app")


def props(t, logical_id):
    return t["Resources"][logical_id]["Properties"]


def container(t, task_logical_id):
    (only,) = props(t, task_logical_id)["ContainerDefinitions"]
    return only


def env(c):
    return {e["Name"]: e["Value"] for e in c.get("Environment", [])}


def statements(role_props):
    return [s for policy in role_props.get("Policies", []) for s in policy["PolicyDocument"]["Statement"]]


def test_lint():
    cfn_lint("app")


def test_backend_container(t):
    task = props(t, "BackendTaskDefinition")
    c = container(t, "BackendTaskDefinition")
    assert env(c) == {
        "AUTH_MODE": "cognito",
        "COGNITO_REGION": {"Ref": "AWS::Region"},
        "COGNITO_USER_POOL_ID": {"Ref": "UserPoolId"},
        "COGNITO_CLIENT_ID": {"Ref": "UserPoolClientId"},
        "UPLOAD_MODE": "s3",
        "S3_BUCKET": {"Ref": "CoversBucketName"},
        "S3_REGION": {"Ref": "AWS::Region"},
        "PUBLIC_FILE_BASE_URL": {"Fn::Sub": "https://${Distribution.DomainName}"},
        "SEED_DEMO_DATA": "true",
        "DB_HOST": {"Ref": "DatabaseEndpoint"},
        "DB_PORT": {"Ref": "DatabasePort"},
        "DB_NAME": {"Ref": "DatabaseName"},
        "DB_SSLMODE": "require",
    }
    assert c["Secrets"] == [
        {"Name": "DB_USER", "ValueFrom": {"Fn::Sub": "${DatabaseSecretArn}:username::"}},
        {"Name": "DB_PASSWORD", "ValueFrom": {"Fn::Sub": "${DatabaseSecretArn}:password::"}},
    ]
    assert "dev" not in env(c).values()  # dev tokens must never be accepted in AWS
    assert (task["Cpu"], task["Memory"]) == ("512", "1024")
    assert task["RuntimePlatform"] == {"OperatingSystemFamily": "LINUX", "CpuArchitecture": "X86_64"}
    assert [p["ContainerPort"] for p in c["PortMappings"]] == [8000]
    assert c["Image"] == {"Ref": "BackendImage"}
    assert task["ExecutionRoleArn"] == {"Fn::GetAtt": ["ExecutionRole", "Arn"]}
    assert task["TaskRoleArn"] == {"Fn::GetAtt": ["BackendTaskRole", "Arn"]}


def test_frontend_container(t):
    task = props(t, "FrontendTaskDefinition")
    c = container(t, "FrontendTaskDefinition")
    assert env(c) == {"API_BASE_URL": "/api", "USE_MOCK": "false",
                      "COGNITO_USER_POOL_ID": {"Ref": "UserPoolId"}, "COGNITO_CLIENT_ID": {"Ref": "UserPoolClientId"}}
    assert (task["Cpu"], task["Memory"]) == ("256", "512")
    assert [p["ContainerPort"] for p in c["PortMappings"]] == [80]
    assert c["Image"] == {"Ref": "FrontendImage"}
    assert task["ExecutionRoleArn"] == {"Fn::GetAtt": ["ExecutionRole", "Arn"]}
    assert "TaskRoleArn" not in task  # the website container calls no AWS API


def test_own_roles(t):
    roles = resources(t, "AWS::IAM::Role")
    assert set(roles) == {"ExecutionRole", "BackendTaskRole"}
    for role in roles.values():
        (trust,) = role["Properties"]["AssumeRolePolicyDocument"]["Statement"]
        assert trust["Principal"] == {"Service": "ecs-tasks.amazonaws.com"}
    execution = roles["ExecutionRole"]["Properties"]
    (managed,) = execution["ManagedPolicyArns"]
    assert sub_text(managed).endswith(":iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy")
    assert statements(execution) == [
        {"Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": {"Ref": "DatabaseSecretArn"}}]
    task = roles["BackendTaskRole"]["Properties"]
    assert "ManagedPolicyArns" not in task
    assert statements(task) == [
        {"Effect": "Allow", "Action": "s3:PutObject", "Resource": {"Fn::Sub": "${CoversBucketArn}/covers/*"}}]
    assert "ecsTaskExecutionRole" not in json.dumps(t)  # the account's shared role isn't ours


def test_services(t):
    for logical_id, group, rule in (("BackendService", "BackendSecurityGroupId", "ApiRule"),
                                    ("FrontendService", "FrontendSecurityGroupId", "WebRule")):
        service = t["Resources"][logical_id]
        p = service["Properties"]
        assert p["DesiredCount"] == 1 and p["LaunchType"] == "FARGATE"
        assert p["NetworkConfiguration"]["AwsvpcConfiguration"] == {
            "AssignPublicIp": "ENABLED", "Subnets": {"Ref": "PublicSubnetIds"}, "SecurityGroups": [{"Ref": group}]}
        deployment = p["DeploymentConfiguration"]
        assert deployment["DeploymentCircuitBreaker"] == {"Enable": True, "Rollback": True}
        assert deployment["MinimumHealthyPercent"] == 100  # the old task serves until the new one is healthy
        assert service["DependsOn"] == rule
    assert props(t, "BackendService")["HealthCheckGracePeriodSeconds"] >= 120  # migrations run at startup


def test_load_balancer_only_serves_cloudfront(t):
    (listener,) = resources(t, "AWS::ElasticLoadBalancingV2::Listener").values()
    (default,) = listener["Properties"]["DefaultActions"]
    assert default["Type"] == "fixed-response" and default["FixedResponseConfig"]["StatusCode"] == "403"
    rules = {r["Properties"]["Priority"]: r["Properties"]
             for r in resources(t, "AWS::ElasticLoadBalancingV2::ListenerRule").values()}
    assert set(rules) == {10, 20}
    for priority, target in ((10, "BackendTargetGroup"), (20, "FrontendTargetGroup")):
        conditions = {c["Field"]: c for c in rules[priority]["Conditions"]}
        assert conditions["http-header"]["HttpHeaderConfig"] == {"HttpHeaderName": "X-Origin-Verify",
                                                                "Values": [ORIGIN_VERIFY]}
        assert rules[priority]["Actions"] == [{"Type": "forward", "TargetGroupArn": {"Ref": target}}]
    assert {c["Field"] for c in rules[10]["Conditions"]} == {"path-pattern", "http-header"}
    assert {c["Field"]: c for c in rules[10]["Conditions"]}["path-pattern"]["PathPatternConfig"] == {"Values": ["/api/*"]}
    assert {c["Field"] for c in rules[20]["Conditions"]} == {"http-header"}
    assert props(t, "BackendTargetGroup")["HealthCheckPath"] == "/api/health"
    assert props(t, "FrontendTargetGroup")["HealthCheckPath"] == "/health"


def test_cloudfront(t):
    config = props(t, "Distribution")["DistributionConfig"]
    default = config["DefaultCacheBehavior"]
    by_path = {b["PathPattern"]: b for b in config["CacheBehaviors"]}
    assert set(by_path) == {"/api/*", "/covers/*"}
    assert all(b["ViewerProtocolPolicy"] == "redirect-to-https" for b in [default, *by_path.values()])
    assert (default["TargetOriginId"], default["CachePolicyId"]) == ("alb", USE_ORIGIN_CACHE_CONTROL)
    api = by_path["/api/*"]
    assert api["TargetOriginId"] == "alb"
    assert sorted(api["AllowedMethods"]) == sorted(["GET", "HEAD", "OPTIONS", "PUT", "PATCH", "POST", "DELETE"])
    assert api["CachePolicyId"] == {"Ref": "ApiCachePolicy"}
    assert api["OriginRequestPolicyId"] == ALL_VIEWER_EXCEPT_HOST
    covers = by_path["/covers/*"]
    assert (covers["TargetOriginId"], covers["CachePolicyId"]) == ("covers", CACHING_OPTIMIZED)
    origins = {o["Id"]: o for o in config["Origins"]}
    assert set(origins) == {"alb", "covers"}
    assert origins["alb"]["DomainName"] == {"Fn::GetAtt": ["LoadBalancer", "DNSName"]}
    assert origins["alb"]["CustomOriginConfig"]["OriginProtocolPolicy"] == "http-only"
    assert origins["alb"]["OriginCustomHeaders"] == [{"HeaderName": "X-Origin-Verify", "HeaderValue": ORIGIN_VERIFY}]
    assert origins["covers"]["DomainName"] == {"Ref": "CoversBucketRegionalDomainName"}
    assert origins["covers"]["OriginAccessControlId"] in ({"Ref": "CoversOriginAccessControl"},
                                                          {"Fn::GetAtt": ["CoversOriginAccessControl", "Id"]})
    errors = {e["ErrorCode"]: e for e in config["CustomErrorResponses"]}
    assert set(errors) == {400, 403, 404, 405, 414, 416, 500, 501, 502, 503, 504}
    assert all(e["ErrorCachingMinTTL"] == 0 for e in errors.values())  # never serve a cached error


def test_api_cache_policy(t):
    config = props(t, "ApiCachePolicy")["CachePolicyConfig"]
    assert (config["MinTTL"], config["DefaultTTL"], config["MaxTTL"]) == (0, 0, 1)
    keys = config["ParametersInCacheKeyAndForwardedToOrigin"]
    assert keys["HeadersConfig"] == {"HeaderBehavior": "whitelist", "Headers": ["Authorization"]}
    assert keys["QueryStringsConfig"] == {"QueryStringBehavior": "all"}


def test_bucket_policy(t):
    p = props(t, "CoversBucketPolicy")
    assert p["Bucket"] == {"Ref": "CoversBucketName"}
    (statement,) = p["PolicyDocument"]["Statement"]
    assert statement == {
        "Effect": "Allow",
        "Principal": {"Service": "cloudfront.amazonaws.com"},
        "Action": "s3:GetObject",
        "Resource": {"Fn::Sub": "${CoversBucketArn}/covers/*"},
        "Condition": {"StringEquals": {"AWS:SourceArn": {
            "Fn::Sub": "arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${Distribution}"}}},
    }


def test_logs(t):
    groups = resources(t, "AWS::Logs::LogGroup").values()
    assert sorted(sub_text(g["Properties"]["LogGroupName"]) for g in groups) == \
        ["/ecs/${Prefix}/backend", "/ecs/${Prefix}/frontend"]
    assert all(g["Properties"]["RetentionInDays"] == 14 for g in groups)


def test_names_use_prefix(t):
    names = name_properties(t)
    assert len(names) >= 12
    for logical_id, key, value in names:
        assert "${Prefix}" in sub_text(value), (logical_id, key, value)


def test_outputs(t):
    assert set(t["Outputs"]) >= {"SiteUrl", "DistributionId", "LoadBalancerDnsName", "ClusterName",
                                 "BackendServiceName", "BackendTaskFamily"}
