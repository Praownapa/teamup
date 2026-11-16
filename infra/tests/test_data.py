"""The data stack: the database and its password, the cover-image bucket, Cognito, and the image repositories."""
import pytest

from conftest import cfn_lint, load_template, name_properties, resources, sub_text


@pytest.fixture(scope="module")
def t():
    return load_template("data")


def props(t, logical_id):
    return t["Resources"][logical_id]["Properties"]


def test_lint():
    cfn_lint("data")


def test_database(t):
    db = t["Resources"]["Database"]
    p = db["Properties"]
    assert db["Type"] == "AWS::RDS::DBInstance"
    assert (p["Engine"], p["EngineVersion"].split(".")[0], p["DBInstanceClass"], p["AllocatedStorage"],
            p["StorageType"]) == ("postgres", "17", "db.t4g.micro", "20", "gp3")
    assert (p["MultiAZ"], p["PubliclyAccessible"], p["DBName"]) == (False, False, "teamup")
    assert db["DeletionPolicy"] == "Delete"
    assert (p["DeleteAutomatedBackups"], p["DeletionProtection"], p["AutoMinorVersionUpgrade"]) == (True, False, False)
    assert p["PreferredMaintenanceWindow"] == "wed:18:00-wed:18:30"  # Thursday 01:00 in Thailand, after the demo
    assert p["DBSubnetGroupName"] == {"Ref": "DatabaseSubnetGroup"}
    assert props(t, "DatabaseSubnetGroup")["SubnetIds"] == {"Ref": "PrivateSubnetIds"}
    assert p["VPCSecurityGroups"] == [{"Ref": "DatabaseSecurityGroupId"}]
    assert "{{resolve:secretsmanager:" in str(p["MasterUserPassword"])
    assert "ManageMasterUserPassword" not in p  # an RDS-managed password rotates every 7 days


def test_no_password_rotation(t):
    # ECS reads the password only when a container starts, so it must not change during the demo period.
    assert not resources(t, "AWS::SecretsManager::RotationSchedule")
    generate = props(t, "DatabaseSecret")["GenerateSecretString"]
    assert generate["GenerateStringKey"] == "password" and generate["PasswordLength"] == 32
    assert all(c in generate["ExcludeCharacters"] for c in "\"@/\\'")


def test_bucket_is_private(t):
    bucket = t["Resources"]["CoversBucket"]
    assert bucket["Properties"]["PublicAccessBlockConfiguration"] == {
        "BlockPublicAcls": True, "BlockPublicPolicy": True, "IgnorePublicAcls": True, "RestrictPublicBuckets": True}
    (rule,) = bucket["Properties"]["CorsConfiguration"]["CorsRules"]
    assert rule["AllowedMethods"] == ["PUT"]
    assert bucket["DeletionPolicy"] == "Delete"


def test_user_pool(t):
    p = props(t, "UserPool")
    assert p["UsernameAttributes"] == ["email"] and p["AutoVerifiedAttributes"] == ["email"]
    policy = p["Policies"]["PasswordPolicy"]
    assert {k: policy[k] for k in ("MinimumLength", "RequireUppercase", "RequireLowercase", "RequireNumbers",
                                   "RequireSymbols")} == {"MinimumLength": 8, "RequireUppercase": True,
                                                          "RequireLowercase": True, "RequireNumbers": True,
                                                          "RequireSymbols": False}  # same rule as the sign-up form
    schema = {attr["Name"]: attr for attr in p["Schema"]}
    assert schema["email"]["Required"] is True and schema["name"]["Required"] is True
    for attr in ("student_id", "major"):  # custom:student_id and custom:major, sent by the sign-up form
        assert schema[attr]["AttributeDataType"] == "String" and schema[attr]["Mutable"] is True
    assert p["UserPoolTier"] == "LITE" and p["DeletionProtection"] == "INACTIVE"
    assert p["AccountRecoverySetting"]["RecoveryMechanisms"] == [{"Name": "verified_email", "Priority": 1}]


def test_app_client(t):
    p = props(t, "UserPoolClient")
    assert p["UserPoolId"] == {"Ref": "UserPool"}
    assert p["GenerateSecret"] is False  # a browser app can't keep a secret
    assert sorted(p["ExplicitAuthFlows"]) == sorted(
        ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_ADMIN_USER_PASSWORD_AUTH"])


def test_admin_group(t):
    (group,) = resources(t, "AWS::Cognito::UserPoolGroup").values()
    assert group["Properties"]["GroupName"] == "admin"
    assert group["Properties"]["UserPoolId"] == {"Ref": "UserPool"}


def test_repositories(t):
    repos = list(resources(t, "AWS::ECR::Repository").values())
    assert sorted(sub_text(r["Properties"]["RepositoryName"]) for r in repos) == ["${Prefix}-backend", "${Prefix}-frontend"]
    assert all(r["Properties"]["EmptyOnDelete"] is True for r in repos)


def test_names_use_prefix(t):
    names = name_properties(t, exempt=frozenset({"DBName", "GroupName"}))
    assert names
    for logical_id, key, value in names:
        assert sub_text(value).startswith("${Prefix}-"), (logical_id, key, value)


def test_outputs(t):
    assert set(t["Outputs"]) >= {
        "DatabaseEndpoint", "DatabasePort", "DatabaseName", "DatabaseSecretArn", "CoversBucketName", "CoversBucketArn",
        "CoversBucketRegionalDomainName", "UserPoolId", "UserPoolClientId", "BackendRepositoryUri",
        "FrontendRepositoryUri"}
