# install

Install warpgate

## Table of contents

- [Requirements](#requirements)
- [Default Variables](#default-variables)
  - [warpgate_admin_password](#warpgate_admin_password)
  - [warpgate_config_file_path](#warpgate_config_file_path)
  - [warpgate_data_path](#warpgate_data_path)
  - [warpgate_database_url](#warpgate_database_url)
  - [warpgate_external_host](#warpgate_external_host)
  - [warpgate_http_certificate](#warpgate_http_certificate)
  - [warpgate_http_cookie_max_age](#warpgate_http_cookie_max_age)
  - [warpgate_http_external_host](#warpgate_http_external_host)
  - [warpgate_http_external_port](#warpgate_http_external_port)
  - [warpgate_http_key](#warpgate_http_key)
  - [warpgate_http_port](#warpgate_http_port)
  - [warpgate_http_proxy_protocol](#warpgate_http_proxy_protocol)
  - [warpgate_http_session_max_age](#warpgate_http_session_max_age)
  - [warpgate_http_sni_certificates](#warpgate_http_sni_certificates)
  - [warpgate_http_trust_x_forwarded_headers](#warpgate_http_trust_x_forwarded_headers)
  - [warpgate_kubernetes_certificate](#warpgate_kubernetes_certificate)
  - [warpgate_kubernetes_enabled](#warpgate_kubernetes_enabled)
  - [warpgate_kubernetes_external_host](#warpgate_kubernetes_external_host)
  - [warpgate_kubernetes_external_port](#warpgate_kubernetes_external_port)
  - [warpgate_kubernetes_key](#warpgate_kubernetes_key)
  - [warpgate_kubernetes_port](#warpgate_kubernetes_port)
  - [warpgate_kubernetes_proxy_protocol](#warpgate_kubernetes_proxy_protocol)
  - [warpgate_kubernetes_session_max_age](#warpgate_kubernetes_session_max_age)
  - [warpgate_log_audit_retention](#warpgate_log_audit_retention)
  - [warpgate_log_format](#warpgate_log_format)
  - [warpgate_log_retention](#warpgate_log_retention)
  - [warpgate_log_send_to](#warpgate_log_send_to)
  - [warpgate_mysql_advertised_version](#warpgate_mysql_advertised_version)
  - [warpgate_mysql_certificate](#warpgate_mysql_certificate)
  - [warpgate_mysql_enabled](#warpgate_mysql_enabled)
  - [warpgate_mysql_external_host](#warpgate_mysql_external_host)
  - [warpgate_mysql_external_port](#warpgate_mysql_external_port)
  - [warpgate_mysql_key](#warpgate_mysql_key)
  - [warpgate_mysql_port](#warpgate_mysql_port)
  - [warpgate_mysql_proxy_protocol](#warpgate_mysql_proxy_protocol)
  - [warpgate_postgres_certificate](#warpgate_postgres_certificate)
  - [warpgate_postgres_enabled](#warpgate_postgres_enabled)
  - [warpgate_postgres_external_host](#warpgate_postgres_external_host)
  - [warpgate_postgres_external_port](#warpgate_postgres_external_port)
  - [warpgate_postgres_key](#warpgate_postgres_key)
  - [warpgate_postgres_port](#warpgate_postgres_port)
  - [warpgate_postgres_proxy_protocol](#warpgate_postgres_proxy_protocol)
  - [warpgate_rdp_certificate](#warpgate_rdp_certificate)
  - [warpgate_rdp_enabled](#warpgate_rdp_enabled)
  - [warpgate_rdp_external_host](#warpgate_rdp_external_host)
  - [warpgate_rdp_external_port](#warpgate_rdp_external_port)
  - [warpgate_rdp_key](#warpgate_rdp_key)
  - [warpgate_rdp_port](#warpgate_rdp_port)
  - [warpgate_rdp_proxy_protocol](#warpgate_rdp_proxy_protocol)
  - [warpgate_record_sessions](#warpgate_record_sessions)
  - [warpgate_recordings_path](#warpgate_recordings_path)
  - [warpgate_service_enabled](#warpgate_service_enabled)
  - [warpgate_service_state](#warpgate_service_state)
  - [warpgate_ssh_enabled](#warpgate_ssh_enabled)
  - [warpgate_ssh_external_host](#warpgate_ssh_external_host)
  - [warpgate_ssh_external_port](#warpgate_ssh_external_port)
  - [warpgate_ssh_host_key_verification](#warpgate_ssh_host_key_verification)
  - [warpgate_ssh_inactivity_timeout](#warpgate_ssh_inactivity_timeout)
  - [warpgate_ssh_keepalive_interval](#warpgate_ssh_keepalive_interval)
  - [warpgate_ssh_keys_path](#warpgate_ssh_keys_path)
  - [warpgate_ssh_port](#warpgate_ssh_port)
  - [warpgate_ssh_proxy_protocol](#warpgate_ssh_proxy_protocol)
  - [warpgate_ssh_target_handshake_timeout](#warpgate_ssh_target_handshake_timeout)
  - [warpgate_sso_providers](#warpgate_sso_providers)
  - [warpgate_system_group](#warpgate_system_group)
  - [warpgate_system_user](#warpgate_system_user)
  - [warpgate_tls_certificate_path](#warpgate_tls_certificate_path)
  - [warpgate_tls_key_path](#warpgate_tls_key_path)
  - [warpgate_version](#warpgate_version)
  - [warpgate_vnc_certificate](#warpgate_vnc_certificate)
  - [warpgate_vnc_enable_ard_auth](#warpgate_vnc_enable_ard_auth)
  - [warpgate_vnc_enabled](#warpgate_vnc_enabled)
  - [warpgate_vnc_external_host](#warpgate_vnc_external_host)
  - [warpgate_vnc_external_port](#warpgate_vnc_external_port)
  - [warpgate_vnc_key](#warpgate_vnc_key)
  - [warpgate_vnc_port](#warpgate_vnc_port)
  - [warpgate_vnc_proxy_protocol](#warpgate_vnc_proxy_protocol)
- [Dependencies](#dependencies)
- [License](#license)
- [Author](#author)

---

## Requirements

- Minimum Ansible version: `2.1`

## Default Variables

### warpgate_admin_password

Warpgate admin password

**_Type:_** string<br />

### warpgate_config_file_path

Warpgate config path

**_Type:_** string<br />

#### Default value

```YAML
warpgate_config_file_path: '{{ warpgate_config_file_directory }}/warpgate.yaml'
```

### warpgate_data_path

Warpgate data path

**_Type:_** string<br />

#### Default value

```YAML
warpgate_data_path: /var/lib/warpgate
```

### warpgate_database_url

Warpgate database URL

**_Type:_** string<br />

#### Default value

```YAML
warpgate_database_url: sqlite:{{ warpgate_data_path }}/warpgate.db
```

### warpgate_external_host

Warpgate external host

**_Type:_** string<br />

#### Default value

```YAML
warpgate_external_host: localhost
```

### warpgate_http_certificate

TLS certificate path for the HTTP listener

**_Type:_** string<br />

#### Default value

```YAML
warpgate_http_certificate: '{{ warpgate_data_path }}/tls.certificate.pem'
```

### warpgate_http_cookie_max_age

Maximum lifetime of the auth cookie

**_Type:_** string<br />

#### Default value

```YAML
warpgate_http_cookie_max_age: 1day
```

### warpgate_http_external_host

Public hostname advertised for the HTTP listener (null = auto)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_http_external_host:
```

### warpgate_http_external_port

Public port advertised for the HTTP listener (null = auto)

**_Type:_** int<br />

#### Default value

```YAML
warpgate_http_external_port:
```

### warpgate_http_key

TLS key path for the HTTP listener

**_Type:_** string<br />

#### Default value

```YAML
warpgate_http_key: '{{ warpgate_data_path }}/tls.key.pem'
```

### warpgate_http_port

Warpgate HTTP port

**_Type:_** int<br />

#### Default value

```YAML
warpgate_http_port: 8888
```

### warpgate_http_proxy_protocol

Accept HAProxy PROXY protocol v1/v2 headers on the HTTP listener

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_http_proxy_protocol: false
```

### warpgate_http_session_max_age

Maximum lifetime of an HTTP session

**_Type:_** string<br />

#### Default value

```YAML
warpgate_http_session_max_age: 30m
```

### warpgate_http_sni_certificates

Additional SNI certificates for the HTTP listener

**_Type:_** list<br />

#### Default value

```YAML
warpgate_http_sni_certificates: []
```

### warpgate_http_trust_x_forwarded_headers

Trust X-Forwarded-* headers (enable only when running behind a trusted reverse proxy)

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_http_trust_x_forwarded_headers: false
```

### warpgate_kubernetes_certificate

TLS certificate path for the Kubernetes listener

**_Type:_** string<br />

#### Default value

```YAML
warpgate_kubernetes_certificate: '{{ warpgate_data_path }}/tls.certificate.pem'
```

### warpgate_kubernetes_enabled

Warpgate Kubernetes enabled

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_kubernetes_enabled: false
```

### warpgate_kubernetes_external_host

Public hostname advertised for the Kubernetes listener (null = auto)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_kubernetes_external_host:
```

### warpgate_kubernetes_external_port

Public port advertised for the Kubernetes listener (null = auto)

**_Type:_** int<br />

#### Default value

```YAML
warpgate_kubernetes_external_port:
```

### warpgate_kubernetes_key

TLS key path for the Kubernetes listener

**_Type:_** string<br />

#### Default value

```YAML
warpgate_kubernetes_key: '{{ warpgate_data_path }}/tls.key.pem'
```

### warpgate_kubernetes_port

Warpgate Kubernetes port

**_Type:_** int<br />

#### Default value

```YAML
warpgate_kubernetes_port: 8443
```

### warpgate_kubernetes_proxy_protocol

Accept HAProxy PROXY protocol v1/v2 headers on the Kubernetes listener

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_kubernetes_proxy_protocol: false
```

### warpgate_kubernetes_session_max_age

Maximum lifetime of a Kubernetes session

**_Type:_** string<br />

#### Default value

```YAML
warpgate_kubernetes_session_max_age: 30m
```

### warpgate_log_audit_retention

Audit log retention duration

**_Type:_** string<br />

#### Default value

```YAML
warpgate_log_audit_retention: 11months 30days 3h 50m 24s
```

### warpgate_log_format

Log output format (text or json)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_log_format: text
```

### warpgate_log_retention

Log retention duration

**_Type:_** string<br />

#### Default value

```YAML
warpgate_log_retention: 7days
```

### warpgate_log_send_to

Remote log endpoint (null = log locally only)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_log_send_to:
```

### warpgate_mysql_advertised_version

MySQL server version advertised to clients during the handshake

**_Type:_** string<br />

#### Default value

```YAML
warpgate_mysql_advertised_version: 8.0.3-Warpgate
```

### warpgate_mysql_certificate

TLS certificate path for the MySQL listener

**_Type:_** string<br />

#### Default value

```YAML
warpgate_mysql_certificate: '{{ warpgate_data_path }}/tls.certificate.pem'
```

### warpgate_mysql_enabled

Warpgate MySQL enabled

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_mysql_enabled: false
```

### warpgate_mysql_external_host

Public hostname advertised for the MySQL listener (null = auto)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_mysql_external_host:
```

### warpgate_mysql_external_port

Public port advertised for the MySQL listener (null = auto)

**_Type:_** int<br />

#### Default value

```YAML
warpgate_mysql_external_port:
```

### warpgate_mysql_key

TLS key path for the MySQL listener

**_Type:_** string<br />

#### Default value

```YAML
warpgate_mysql_key: '{{ warpgate_data_path }}/tls.key.pem'
```

### warpgate_mysql_port

Warpgate MySQL port

**_Type:_** int<br />

#### Default value

```YAML
warpgate_mysql_port: 33306
```

### warpgate_mysql_proxy_protocol

Accept HAProxy PROXY protocol v1/v2 headers on the MySQL listener

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_mysql_proxy_protocol: false
```

### warpgate_postgres_certificate

TLS certificate path for the PostgreSQL listener

**_Type:_** string<br />

#### Default value

```YAML
warpgate_postgres_certificate: '{{ warpgate_data_path }}/tls.certificate.pem'
```

### warpgate_postgres_enabled

Warpgate PostgreSQL enabled

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_postgres_enabled: false
```

### warpgate_postgres_external_host

Public hostname advertised for the PostgreSQL listener (null = auto)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_postgres_external_host:
```

### warpgate_postgres_external_port

Public port advertised for the PostgreSQL listener (null = auto)

**_Type:_** int<br />

#### Default value

```YAML
warpgate_postgres_external_port:
```

### warpgate_postgres_key

TLS key path for the PostgreSQL listener

**_Type:_** string<br />

#### Default value

```YAML
warpgate_postgres_key: '{{ warpgate_data_path }}/tls.key.pem'
```

### warpgate_postgres_port

Warpgate PostgreSQL port

**_Type:_** int<br />

#### Default value

```YAML
warpgate_postgres_port: 55432
```

### warpgate_postgres_proxy_protocol

Accept HAProxy PROXY protocol v1/v2 headers on the PostgreSQL listener

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_postgres_proxy_protocol: false
```

### warpgate_rdp_certificate

TLS certificate path for the RDP listener

**_Type:_** string<br />

#### Default value

```YAML
warpgate_rdp_certificate: '{{ warpgate_data_path }}/tls.certificate.pem'
```

### warpgate_rdp_enabled

Warpgate RDP enabled

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_rdp_enabled: false
```

### warpgate_rdp_external_host

Public hostname advertised for the RDP listener (null = auto)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_rdp_external_host:
```

### warpgate_rdp_external_port

Public port advertised for the RDP listener (null = auto)

**_Type:_** int<br />

#### Default value

```YAML
warpgate_rdp_external_port:
```

### warpgate_rdp_key

TLS key path for the RDP listener

**_Type:_** string<br />

#### Default value

```YAML
warpgate_rdp_key: '{{ warpgate_data_path }}/tls.key.pem'
```

### warpgate_rdp_port

Warpgate RDP port

**_Type:_** int<br />

#### Default value

```YAML
warpgate_rdp_port: 3389
```

### warpgate_rdp_proxy_protocol

Accept HAProxy PROXY protocol v1/v2 headers on the RDP listener

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_rdp_proxy_protocol: false
```

### warpgate_record_sessions

Warpgate record sessions

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_record_sessions: true
```

### warpgate_recordings_path

Path where session recordings are stored

**_Type:_** string<br />

#### Default value

```YAML
warpgate_recordings_path: '{{ warpgate_data_path }}/recordings'
```

### warpgate_service_enabled

Enable warpgate service

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_service_enabled: true
```

### warpgate_service_state

warpgate service desired state

**_Type:_** string<br />

#### Default value

```YAML
warpgate_service_state: started
```

### warpgate_ssh_enabled

Warpgate SSH enabled

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_ssh_enabled: false
```

### warpgate_ssh_external_host

Public hostname advertised for the SSH listener (null = auto)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_ssh_external_host:
```

### warpgate_ssh_external_port

Public port advertised for the SSH listener (null = auto)

**_Type:_** int<br />

#### Default value

```YAML
warpgate_ssh_external_port:
```

### warpgate_ssh_host_key_verification

SSH target host key verification mode (prompt, auto, strict)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_ssh_host_key_verification: prompt
```

### warpgate_ssh_inactivity_timeout

Idle timeout before an SSH session is closed

**_Type:_** string<br />

#### Default value

```YAML
warpgate_ssh_inactivity_timeout: 5m
```

### warpgate_ssh_keepalive_interval

Keepalive interval for SSH sessions (null disables keepalive)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_ssh_keepalive_interval:
```

### warpgate_ssh_keys_path

Directory holding Warpgate's SSH host keys

**_Type:_** string<br />

#### Default value

```YAML
warpgate_ssh_keys_path: '{{ warpgate_data_path }}/ssh-keys'
```

### warpgate_ssh_port

Warpgate SSH port

**_Type:_** int<br />

#### Default value

```YAML
warpgate_ssh_port: 2222
```

### warpgate_ssh_proxy_protocol

Accept HAProxy PROXY protocol v1/v2 headers on the SSH listener

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_ssh_proxy_protocol: false
```

### warpgate_ssh_target_handshake_timeout

Deadline for a target to accept the connection and complete key exchange (0s waits forever)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_ssh_target_handshake_timeout: 30s
```

### warpgate_sso_providers

Warpgate SSO providers

**_Type:_** list<br />

#### Default value

```YAML
warpgate_sso_providers: []
```

### warpgate_system_group

System group name to create

**_Type:_** string<br />

#### Default value

```YAML
warpgate_system_group: warpgate
```

### warpgate_system_user

System user name to create

**_Type:_** string<br />

#### Default value

```YAML
warpgate_system_user: warpgate
```

### warpgate_tls_certificate_path

Default TLS certificate path used by HTTP / Kubernetes / MySQL / PostgreSQL listeners

**_Type:_** string<br />

#### Default value

```YAML
warpgate_tls_certificate_path: '{{ warpgate_data_path }}/tls.certificate.pem'
```

### warpgate_tls_key_path

Default TLS key path used by HTTP / Kubernetes / MySQL / PostgreSQL listeners

**_Type:_** string<br />

#### Default value

```YAML
warpgate_tls_key_path: '{{ warpgate_data_path }}/tls.key.pem'
```

### warpgate_version

warpgate version to install

**_Type:_** string<br />

#### Default value

```YAML
warpgate_version: 0.30.2
```

### warpgate_vnc_certificate

TLS certificate path for the VNC listener

**_Type:_** string<br />

#### Default value

```YAML
warpgate_vnc_certificate: '{{ warpgate_data_path }}/tls.certificate.pem'
```

### warpgate_vnc_enable_ard_auth

Enable Apple-DH (ARD / type 30) auth; it does not support TLS unlike VeNCrypt

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_vnc_enable_ard_auth: false
```

### warpgate_vnc_enabled

Warpgate VNC enabled

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_vnc_enabled: false
```

### warpgate_vnc_external_host

Public hostname advertised for the VNC listener (null = auto)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_vnc_external_host:
```

### warpgate_vnc_external_port

Public port advertised for the VNC listener (null = auto)

**_Type:_** int<br />

#### Default value

```YAML
warpgate_vnc_external_port:
```

### warpgate_vnc_key

TLS key path for the VNC listener

**_Type:_** string<br />

#### Default value

```YAML
warpgate_vnc_key: '{{ warpgate_data_path }}/tls.key.pem'
```

### warpgate_vnc_port

Warpgate VNC port

**_Type:_** int<br />

#### Default value

```YAML
warpgate_vnc_port: 5900
```

### warpgate_vnc_proxy_protocol

Accept HAProxy PROXY protocol v1/v2 headers on the VNC listener

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_vnc_proxy_protocol: false
```

## Dependencies

None.

## License

MPL2

## Author

Clément Hubert
