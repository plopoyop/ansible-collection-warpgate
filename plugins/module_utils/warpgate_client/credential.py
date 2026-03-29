"""
Credential management for the Warpgate API

This module provides functions to manage user credentials (password, public key, SSO, certificate).
"""

from typing import Any, Dict, List

from .client import WarpgateAPIError


class PasswordCredential:
    """Represents a password credential for a user"""

    def __init__(self, id: str = "", password: str = ""):
        self.id = id
        self.password = password

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PasswordCredential":
        """Create a PasswordCredential from a dictionary"""
        return cls(id=data.get("id", ""), password=data.get("password", ""))


class PublicKeyCredential:
    """Represents a public key credential for a user"""

    def __init__(
        self,
        id: str = "",
        label: str = "",
        openssh_public_key: str = "",
        date_added: str = "",
        last_used: str = "",
    ):
        self.id = id
        self.label = label
        self.openssh_public_key = openssh_public_key
        self.date_added = date_added
        self.last_used = last_used

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PublicKeyCredential":
        """Create a PublicKeyCredential from a dictionary"""
        return cls(
            id=data.get("id", ""),
            label=data.get("label", ""),
            openssh_public_key=data.get("openssh_public_key", ""),
            date_added=data.get("date_added", ""),
            last_used=data.get("last_used", ""),
        )


class SsoCredential:
    """Represents an SSO credential for a user"""

    def __init__(self, id: str = "", provider: str = "", email: str = ""):
        self.id = id
        self.provider = provider
        self.email = email

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SsoCredential":
        """Create an SsoCredential from a dictionary"""
        return cls(
            id=data.get("id", ""),
            provider=data.get("provider", ""),
            email=data.get("email", ""),
        )


def add_password_credential(client, user_id: str, password: str) -> PasswordCredential:
    """
    Adds a password credential to the specified user.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        password: Password value

    Returns:
        Created PasswordCredential object
    """
    body = {"password": password}
    response = client._request("POST", f"/users/{user_id}/credentials/passwords", body)
    return PasswordCredential.from_dict(response)


def get_password_credentials(client, user_id: str) -> List[PasswordCredential]:
    """
    Retrieves all password credentials for a user.
    Note: The password values are not returned for security reasons, only the IDs.

    Args:
        client: WarpgateClient instance
        user_id: User ID

    Returns:
        List of PasswordCredential objects (with IDs only, no password values)
    """
    try:
        response = client._request("GET", f"/users/{user_id}/credentials/passwords")
        return [PasswordCredential.from_dict(cred) for cred in response]
    except WarpgateAPIError as e:
        if e.status_code == 404:
            # Endpoint might not exist, return empty list
            return []
        raise


def delete_password_credential(client, user_id: str, credential_id: str) -> None:
    """
    Removes a password credential from a user.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        credential_id: Credential ID to delete
    """
    client._request("DELETE", f"/users/{user_id}/credentials/passwords/{credential_id}")


def add_public_key_credential(
    client, user_id: str, label: str, public_key: str
) -> PublicKeyCredential:
    """
    Adds a public key credential to the specified user.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        label: Label for the public key
        public_key: OpenSSH public key

    Returns:
        Created PublicKeyCredential object
    """
    body = {"label": label, "openssh_public_key": public_key}
    response = client._request(
        "POST", f"/users/{user_id}/credentials/public-keys", body
    )
    return PublicKeyCredential.from_dict(response)


def get_public_key_credentials(client, user_id: str) -> List[PublicKeyCredential]:
    """
    Retrieves all public key credentials for a user.

    Args:
        client: WarpgateClient instance
        user_id: User ID

    Returns:
        List of PublicKeyCredential objects
    """
    response = client._request("GET", f"/users/{user_id}/credentials/public-keys")
    return [PublicKeyCredential.from_dict(cred) for cred in response]


def update_public_key_credential(
    client, user_id: str, credential_id: str, label: str, public_key: str
) -> PublicKeyCredential:
    """
    Updates an existing public key credential.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        credential_id: Credential ID to update
        label: Updated label
        public_key: Updated OpenSSH public key

    Returns:
        Updated PublicKeyCredential object
    """
    body = {"label": label, "openssh_public_key": public_key}
    response = client._request(
        "PUT", f"/users/{user_id}/credentials/public-keys/{credential_id}", body
    )
    return PublicKeyCredential.from_dict(response)


def delete_public_key_credential(client, user_id: str, credential_id: str) -> None:
    """
    Removes a public key credential from a user.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        credential_id: Credential ID to delete
    """
    client._request(
        "DELETE", f"/users/{user_id}/credentials/public-keys/{credential_id}"
    )


def get_sso_credentials(client, user_id: str) -> List[SsoCredential]:
    """
    Retrieves all SSO credentials for a user.

    Args:
        client: WarpgateClient instance
        user_id: User ID

    Returns:
        List of SsoCredential objects
    """
    response = client._request("GET", f"/users/{user_id}/credentials/sso")
    return [SsoCredential.from_dict(cred) for cred in response]


def add_sso_credential(
    client, user_id: str, provider: str, email: str
) -> SsoCredential:
    """
    Adds an SSO credential to the specified user.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        provider: SSO provider name
        email: Email address for SSO

    Returns:
        Created SsoCredential object
    """
    body = {"provider": provider, "email": email}
    response = client._request("POST", f"/users/{user_id}/credentials/sso", body)
    return SsoCredential.from_dict(response)


def update_sso_credential(
    client, user_id: str, credential_id: str, provider: str, email: str
) -> SsoCredential:
    """
    Updates an existing SSO credential.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        credential_id: Credential ID to update
        provider: Updated SSO provider name
        email: Updated email address

    Returns:
        Updated SsoCredential object
    """
    body = {"provider": provider, "email": email}
    response = client._request(
        "PUT", f"/users/{user_id}/credentials/sso/{credential_id}", body
    )
    return SsoCredential.from_dict(response)


def delete_sso_credential(client, user_id: str, credential_id: str) -> None:
    """
    Removes an SSO credential from a user.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        credential_id: Credential ID to delete
    """
    client._request("DELETE", f"/users/{user_id}/credentials/sso/{credential_id}")


class CertificateCredential:
    """Represents a certificate credential for a user (used for Kubernetes mTLS)"""

    def __init__(
        self,
        id: str = "",
        label: str = "",
        date_added: str = "",
        last_used: str = "",
        fingerprint: str = "",
    ):
        self.id = id
        self.label = label
        self.date_added = date_added
        self.last_used = last_used
        self.fingerprint = fingerprint

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CertificateCredential":
        """Create a CertificateCredential from a dictionary"""
        return cls(
            id=data.get("id", ""),
            label=data.get("label", ""),
            date_added=data.get("date_added", ""),
            last_used=data.get("last_used", ""),
            fingerprint=data.get("fingerprint", ""),
        )


class IssuedCertificateCredential:
    """Represents a newly issued certificate credential (returned by the issue endpoint)"""

    def __init__(
        self, credential: CertificateCredential = None, certificate_pem: str = ""
    ):
        self.credential = credential or CertificateCredential()
        self.certificate_pem = certificate_pem

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IssuedCertificateCredential":
        """Create an IssuedCertificateCredential from a dictionary"""
        cred_data = data.get("credential", {})
        return cls(
            credential=CertificateCredential.from_dict(cred_data),
            certificate_pem=data.get("certificate_pem", ""),
        )


def get_certificate_credentials(client, user_id: str) -> List[CertificateCredential]:
    """
    Retrieves all certificate credentials for a user.

    Args:
        client: WarpgateClient instance
        user_id: User ID

    Returns:
        List of CertificateCredential objects
    """
    try:
        response = client._request("GET", f"/users/{user_id}/credentials/certificates")
        return [CertificateCredential.from_dict(cred) for cred in response]
    except WarpgateAPIError as e:
        if e.status_code == 404:
            return []
        raise


def issue_certificate_credential(
    client, user_id: str, label: str, public_key_pem: str
) -> IssuedCertificateCredential:
    """
    Issues a new certificate credential for a user. The server signs the provided
    public key using Warpgate's built-in CA.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        label: Label for the certificate
        public_key_pem: PEM-encoded public key to be signed

    Returns:
        IssuedCertificateCredential with the credential metadata and signed certificate PEM
    """
    body = {"label": label, "public_key_pem": public_key_pem}
    response = client._request(
        "POST", f"/users/{user_id}/credentials/certificates", body
    )
    return IssuedCertificateCredential.from_dict(response)


def update_certificate_credential(
    client, user_id: str, credential_id: str, label: str
) -> CertificateCredential:
    """
    Updates an existing certificate credential (label only).

    Args:
        client: WarpgateClient instance
        user_id: User ID
        credential_id: Credential ID to update
        label: Updated label

    Returns:
        Updated CertificateCredential object
    """
    body = {"label": label}
    response = client._request(
        "PATCH", f"/users/{user_id}/credentials/certificates/{credential_id}", body
    )
    return CertificateCredential.from_dict(response)


def delete_certificate_credential(client, user_id: str, credential_id: str) -> None:
    """
    Revokes and deletes a certificate credential from a user.

    Args:
        client: WarpgateClient instance
        user_id: User ID
        credential_id: Credential ID to revoke
    """
    client._request(
        "DELETE", f"/users/{user_id}/credentials/certificates/{credential_id}"
    )
