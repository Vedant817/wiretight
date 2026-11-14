"""Software ES256 authenticator: real CBOR and real signatures, test-only.

This exercises the installed WebAuthn verifier without mocking it. It is not
evidence of physical-device or browser biometric/passkey acceptance.
"""

import hashlib
import json
import secrets

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from webauthn.helpers.bytes_to_base64url import bytes_to_base64url


class Authenticator:
    def __init__(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = secrets.token_bytes(32)
        self.count = 0

    def _client(self, options, ceremony_type, origin):
        return json.dumps(
            {
                "type": ceremony_type,
                "challenge": options["challenge"],
                "origin": origin,
                "crossOrigin": False,
            },
            separators=(",", ":"),
        ).encode()

    def register(self, options, *, origin="http://localhost:8000", verified=True):
        public = self.key.public_key().public_numbers()
        cose = cbor2.dumps(
            {1: 2, 3: -7, -1: 1, -2: public.x.to_bytes(32), -3: public.y.to_bytes(32)}
        )
        data = (
            hashlib.sha256(options["rp"]["id"].encode()).digest()
            + bytes([0x45 if verified else 0x41])
            + self.count.to_bytes(4)
            + bytes(16)
            + len(self.credential_id).to_bytes(2)
            + self.credential_id
            + cose
        )
        credential_id = bytes_to_base64url(self.credential_id)
        return {
            "id": credential_id,
            "rawId": credential_id,
            "type": "public-key",
            "response": {
                "clientDataJSON": bytes_to_base64url(
                    self._client(options, "webauthn.create", origin)
                ),
                "attestationObject": bytes_to_base64url(
                    cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": data})
                ),
            },
        }

    def sign(self, options, *, origin="http://localhost:8000", verified=True):
        self.count += 1
        client = self._client(options, "webauthn.get", origin)
        data = (
            hashlib.sha256(options["rpId"].encode()).digest()
            + bytes([0x05 if verified else 0x01])
            + self.count.to_bytes(4)
        )
        signature = self.key.sign(data + hashlib.sha256(client).digest(), ec.ECDSA(hashes.SHA256()))
        credential_id = bytes_to_base64url(self.credential_id)
        return {
            "id": credential_id,
            "rawId": credential_id,
            "type": "public-key",
            "response": {
                "clientDataJSON": bytes_to_base64url(client),
                "authenticatorData": bytes_to_base64url(data),
                "signature": bytes_to_base64url(signature),
                "userHandle": None,
            },
        }
