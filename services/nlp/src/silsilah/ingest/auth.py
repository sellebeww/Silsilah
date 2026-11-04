# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Verifikasi JWT Supabase (opsional). Hanya dipakai sebagai kunci rate limit, tidak disimpan."""

import jwt


class InvalidTokenError(ValueError):
    pass


class TokenVerifier:
    """HS256 dengan SUPABASE_JWT_SECRET (kunci lama) atau ES256/RS256 lewat JWKS proyek (kunci baru)."""

    def __init__(self, supabase_url: str | None, jwt_secret: str | None) -> None:
        self._secret = jwt_secret
        self._jwks = (
            jwt.PyJWKClient(f"{supabase_url}/auth/v1/.well-known/jwks.json") if supabase_url else None
        )

    def subject(self, token: str) -> str:
        try:
            alg = jwt.get_unverified_header(token).get("alg")
            key: object
            if alg == "HS256" and self._secret:
                key = self._secret
            elif alg in ("ES256", "RS256") and self._jwks:
                key = self._jwks.get_signing_key_from_jwt(token).key
            else:
                raise InvalidTokenError("algoritma token tidak didukung")
            # algoritma dikunci ke header yang sudah dicek agar tidak terjadi kebingungan algoritma
            claims = jwt.decode(token, key, algorithms=[alg], audience="authenticated")  # type: ignore[arg-type]
        except (jwt.PyJWTError, KeyError):
            raise InvalidTokenError("token tidak valid") from None
        return str(claims["sub"])
