"""The network stack: TeamUp's own VPC, no NAT gateway, a private database, and tight firewall rules."""
import pytest

from conftest import cfn_lint, load_template, resources


@pytest.fixture(scope="module")
def t():
    return load_template("network")


def test_lint():
    cfn_lint("network")


def test_no_nat_or_elastic_ip(t):
    # A NAT gateway costs about $45 a month; the containers use public IPs instead.
    assert not resources(t, "AWS::EC2::NatGateway")
    assert not resources(t, "AWS::EC2::EIP")


def test_vpc_dns(t):
    (vpc,) = resources(t, "AWS::EC2::VPC").values()
    assert vpc["Properties"]["EnableDnsSupport"] is True
    assert vpc["Properties"]["EnableDnsHostnames"] is True


def test_subnets(t):
    subnets = resources(t, "AWS::EC2::Subnet")
    assert set(subnets) == {"PublicSubnetA", "PublicSubnetB", "PrivateSubnetA", "PrivateSubnetB"}
    for name in ("PublicSubnetA", "PublicSubnetB"):
        assert subnets[name]["Properties"]["MapPublicIpOnLaunch"] is True
    for name in ("PrivateSubnetA", "PrivateSubnetB"):
        assert not subnets[name]["Properties"].get("MapPublicIpOnLaunch", False)
    for kind in ("Public", "Private"):
        for suffix, index in (("A", 0), ("B", 1)):
            assert subnets[f"{kind}Subnet{suffix}"]["Properties"]["AvailabilityZone"] == \
                {"Fn::Select": [index, {"Fn::GetAZs": ""}]}


def test_private_subnets_have_no_internet_route(t):
    routes = resources(t, "AWS::EC2::Route").values()
    assert all(r["Properties"]["RouteTableId"] != {"Ref": "PrivateRouteTable"} for r in routes)
    associations = [a["Properties"] for a in resources(t, "AWS::EC2::SubnetRouteTableAssociation").values()]
    for subnet in ("PrivateSubnetA", "PrivateSubnetB"):
        assert {"SubnetId": {"Ref": subnet}, "RouteTableId": {"Ref": "PrivateRouteTable"}} in associations


def test_firewall_rules(t):
    expected = {
        "AlbSecurityGroup": (80, {"SourcePrefixListId": {"Ref": "CloudFrontPrefixListId"}}),
        "BackendSecurityGroup": (8000, {"SourceSecurityGroupId": {"Ref": "AlbSecurityGroup"}}),
        "FrontendSecurityGroup": (80, {"SourceSecurityGroupId": {"Ref": "AlbSecurityGroup"}}),
        "DatabaseSecurityGroup": (5432, {"SourceSecurityGroupId": {"Ref": "BackendSecurityGroup"}}),
    }
    groups = resources(t, "AWS::EC2::SecurityGroup")
    assert set(groups) == set(expected)
    for name, (port, source) in expected.items():
        (rule,) = groups[name]["Properties"]["SecurityGroupIngress"]
        rule = {k: v for k, v in rule.items() if k != "Description"}
        assert rule == {"IpProtocol": "tcp", "FromPort": port, "ToPort": port, **source}, name


def test_outputs(t):
    assert set(t["Outputs"]) >= {"VpcId", "PublicSubnetIds", "PrivateSubnetIds", "AlbSecurityGroupId",
                                 "BackendSecurityGroupId", "FrontendSecurityGroupId", "DatabaseSecurityGroupId"}
