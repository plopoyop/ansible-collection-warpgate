"""Tests for model classes: from_dict / to_dict round-trips and edge cases."""

from warpgate_client.admin_role import PERMISSION_FIELDS, AdminRole
from warpgate_client.credential import (
    CertificateCredential,
    IssuedCertificateCredential,
    PasswordCredential,
    PublicKeyCredential,
    SsoCredential,
)
from warpgate_client.role import Role
from warpgate_client.target import TLS, Target
from warpgate_client.target_group import TargetGroup
from warpgate_client.ticket import Ticket, TicketAndSecret
from warpgate_client.user import User, UserRequireCredentialsPolicy

# ---------------------------------------------------------------------------
# UserRequireCredentialsPolicy
# ---------------------------------------------------------------------------


class TestCredentialPolicy:
    def test_to_dict_with_values(self):
        p = UserRequireCredentialsPolicy(
            http=["Password"], ssh=["PublicKey", "Password"]
        )
        assert p.to_dict() == {"http": ["Password"], "ssh": ["PublicKey", "Password"]}

    def test_to_dict_empty_when_no_policies(self):
        p = UserRequireCredentialsPolicy()
        assert p.to_dict() == {}

    def test_to_dict_empty_lists_are_excluded(self):
        """Empty lists are falsy — to_dict should return {}."""
        p = UserRequireCredentialsPolicy(http=[], ssh=[], mysql=[], postgres=[])
        assert p.to_dict() == {}

    def test_to_dict_partial(self):
        p = UserRequireCredentialsPolicy(ssh=["Password"])
        assert p.to_dict() == {"ssh": ["Password"]}

    def test_to_dict_none_fields_excluded(self):
        p = UserRequireCredentialsPolicy(http=None, ssh=["Totp"])
        assert p.to_dict() == {"ssh": ["Totp"]}

    def test_to_dict_with_kubernetes(self):
        p = UserRequireCredentialsPolicy(kubernetes=["Certificate", "Password"])
        assert p.to_dict() == {"kubernetes": ["Certificate", "Password"]}

    def test_to_dict_all_protocols(self):
        p = UserRequireCredentialsPolicy(
            http=["Password"],
            ssh=["PublicKey"],
            mysql=["Password"],
            postgres=["Password"],
            kubernetes=["Certificate"],
        )
        d = p.to_dict()
        assert d == {
            "http": ["Password"],
            "ssh": ["PublicKey"],
            "mysql": ["Password"],
            "postgres": ["Password"],
            "kubernetes": ["Certificate"],
        }


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class TestUser:
    def test_from_dict_minimal(self):
        u = User.from_dict({"id": "u1", "username": "alice"})
        assert u.id == "u1"
        assert u.username == "alice"
        assert u.description == ""
        assert u.credential_policy is None

    def test_from_dict_with_policy(self):
        data = {
            "id": "u1",
            "username": "alice",
            "description": "admin",
            "credential_policy": {"http": ["Password"], "ssh": ["PublicKey"]},
        }
        u = User.from_dict(data)
        assert u.credential_policy is not None
        assert u.credential_policy.http == ["Password"]
        assert u.credential_policy.ssh == ["PublicKey"]
        assert u.credential_policy.mysql is None
        assert u.credential_policy.kubernetes is None

    def test_from_dict_with_kubernetes_policy(self):
        data = {
            "id": "u1",
            "username": "alice",
            "credential_policy": {"kubernetes": ["Certificate"]},
        }
        u = User.from_dict(data)
        assert u.credential_policy is not None
        assert u.credential_policy.kubernetes == ["Certificate"]
        assert u.credential_policy.http is None

    def test_from_dict_null_policy(self):
        u = User.from_dict({"id": "u1", "username": "alice", "credential_policy": None})
        assert u.credential_policy is None

    def test_from_dict_empty_dict_policy(self):
        u = User.from_dict({"id": "u1", "username": "alice", "credential_policy": {}})
        assert u.credential_policy is None

    def test_to_dict_round_trip(self):
        data = {
            "id": "u1",
            "username": "alice",
            "description": "Alice",
            "credential_policy": {"ssh": ["PublicKey"]},
            "rate_limit_bytes_per_second": 1024,
            "ldap_server_id": "ldap1",
            "allowed_ip_ranges": ["10.0.0.0/8"],
        }
        assert User.from_dict(data).to_dict() == data

    def test_to_dict_without_policy(self):
        d = User.from_dict({"id": "u1", "username": "alice"}).to_dict()
        assert d["credential_policy"] == {}
        assert d["rate_limit_bytes_per_second"] is None
        assert d["allowed_ip_ranges"] == []


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------


class TestRole:
    def test_from_dict(self):
        r = Role.from_dict(
            {"id": "r1", "name": "developers", "description": "Dev team"}
        )
        assert r.id == "r1"
        assert r.name == "developers"
        assert r.description == "Dev team"

    def test_from_dict_minimal(self):
        r = Role.from_dict({"id": "r1", "name": "ops"})
        assert r.description == ""

    def test_to_dict_round_trip(self):
        data = {
            "id": "r1",
            "name": "developers",
            "description": "Dev team",
            "is_default": True,
        }
        assert Role.from_dict(data).to_dict() == data


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------


class TestPasswordCredential:
    def test_from_dict(self):
        # The admin API's ExistingPasswordCredential only returns the id;
        # a ``password`` key in the payload is ignored by design.
        c = PasswordCredential.from_dict({"id": "c1", "password": "secret"})
        assert c.id == "c1"

    def test_from_dict_defaults(self):
        c = PasswordCredential.from_dict({})
        assert c.id == ""


class TestPublicKeyCredential:
    def test_from_dict(self):
        c = PublicKeyCredential.from_dict(
            {
                "id": "pk1",
                "label": "laptop",
                "openssh_public_key": "ssh-ed25519 AAAA...",
                "date_added": "2024-01-01",
                "last_used": "2024-06-01",
            }
        )
        assert c.label == "laptop"
        assert c.openssh_public_key == "ssh-ed25519 AAAA..."

    def test_from_dict_defaults(self):
        c = PublicKeyCredential.from_dict({})
        assert c.id == ""
        assert c.label == ""


class TestSsoCredential:
    def test_from_dict(self):
        c = SsoCredential.from_dict(
            {"id": "s1", "provider": "google", "email": "a@b.com"}
        )
        assert c.provider == "google"
        assert c.email == "a@b.com"


class TestCertificateCredential:
    def test_from_dict(self):
        c = CertificateCredential.from_dict(
            {
                "id": "cert1",
                "label": "laptop-cert",
                "date_added": "2026-01-15T10:00:00Z",
                "last_used": "2026-01-16T12:00:00Z",
                "fingerprint": "SHA256:abc123",
            }
        )
        assert c.id == "cert1"
        assert c.label == "laptop-cert"
        assert c.fingerprint == "SHA256:abc123"
        assert c.date_added == "2026-01-15T10:00:00Z"
        assert c.last_used == "2026-01-16T12:00:00Z"

    def test_from_dict_defaults(self):
        c = CertificateCredential.from_dict({})
        assert c.id == ""
        assert c.label == ""
        assert c.fingerprint == ""


class TestIssuedCertificateCredential:
    def test_from_dict(self):
        ic = IssuedCertificateCredential.from_dict(
            {
                "credential": {
                    "id": "cert1",
                    "label": "my-cert",
                    "fingerprint": "SHA256:xyz",
                },
                "certificate_pem": "-----BEGIN CERTIFICATE-----\nABC\n-----END CERTIFICATE-----",
            }
        )
        assert ic.credential.id == "cert1"
        assert ic.credential.label == "my-cert"
        assert ic.certificate_pem.startswith("-----BEGIN CERTIFICATE-----")

    def test_from_dict_defaults(self):
        ic = IssuedCertificateCredential.from_dict({})
        assert ic.credential.id == ""
        assert ic.certificate_pem == ""


# ---------------------------------------------------------------------------
# Target / TLS
# ---------------------------------------------------------------------------


class TestTLS:
    def test_to_dict(self):
        t = TLS(mode="Required", verify=True)
        assert t.to_dict() == {"mode": "Required", "verify": True}


class TestTarget:
    def test_from_dict(self):
        t = Target.from_dict(
            {
                "id": "t1",
                "name": "prod-ssh",
                "description": "Production",
                "group_id": "g1",
                "allow_roles": ["r1", "r2"],
                "options": {"kind": "Ssh", "host": "10.0.0.1"},
            }
        )
        assert t.id == "t1"
        assert t.allow_roles == ["r1", "r2"]
        assert t.options["kind"] == "Ssh"

    def test_from_dict_defaults(self):
        t = Target.from_dict({"id": "t1", "name": "web"})
        assert t.description == ""
        assert t.allow_roles == []
        assert t.options == {}

    def test_to_dict_round_trip(self):
        data = {
            "id": "t1",
            "name": "web",
            "description": "Web server",
            "group_id": "g1",
            "allow_roles": ["r1"],
            "options": {"kind": "Ssh"},
            "rate_limit_bytes_per_second": 2048,
        }
        assert Target.from_dict(data).to_dict() == data


# ---------------------------------------------------------------------------
# TargetGroup
# ---------------------------------------------------------------------------


class TestTargetGroup:
    def test_from_dict(self):
        g = TargetGroup.from_dict(
            {"id": "g1", "name": "prod", "description": "Prod", "color": "Danger"}
        )
        assert g.color == "Danger"

    def test_from_dict_null_color(self):
        g = TargetGroup.from_dict({"id": "g1", "name": "dev", "color": None})
        assert g.color == ""

    def test_to_dict_round_trip(self):
        data = {"id": "g1", "name": "prod", "description": "Prod", "color": "Danger"}
        assert TargetGroup.from_dict(data).to_dict() == data


# ---------------------------------------------------------------------------
# AdminRole
# ---------------------------------------------------------------------------


class TestAdminRole:
    def test_to_dict_exposes_every_permission(self):
        d = AdminRole.from_dict(
            {"id": "a1", "name": "auditor", "sessions_view": True}
        ).to_dict()
        assert d["id"] == "a1"
        assert d["name"] == "auditor"
        assert d["permissions"]["sessions_view"] is True
        assert set(d["permissions"]) == set(PERMISSION_FIELDS)
        assert all(
            v is False for k, v in d["permissions"].items() if k != "sessions_view"
        )

    def test_to_dict_is_a_copy(self):
        role = AdminRole.from_dict({"id": "a1", "name": "auditor"})
        role.to_dict()["permissions"]["config_edit"] = True
        assert role.permissions["config_edit"] is False


# ---------------------------------------------------------------------------
# Ticket / TicketAndSecret
# ---------------------------------------------------------------------------


class TestTicket:
    def test_from_dict(self):
        t = Ticket.from_dict(
            {
                "id": "tk1",
                "username": "admin",
                "target": "web",
                "uses_left": "3",
                "expiry": "2099-12-31",
            }
        )
        assert t.id == "tk1"
        assert t.uses_left == "3"

    def test_from_dict_defaults(self):
        t = Ticket.from_dict({})
        assert t.id == ""


class TestTicketAndSecret:
    def test_from_dict(self):
        ts = TicketAndSecret.from_dict(
            {
                "ticket": {"id": "tk1", "username": "admin"},
                "secret": "s3cr3t",
            }
        )
        assert ts.secret == "s3cr3t"
        assert ts.ticket.id == "tk1"
