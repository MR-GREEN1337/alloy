from src.core.security import verify_password, get_password_hash, create_access_token, decode_token

def test_password_hashing():
    password = "plain_password"
    hashed_password = get_password_hash(password)
    assert hashed_password != password
    assert verify_password(password, hashed_password)
    assert not verify_password("wrong_password", hashed_password)

def test_jwt_token_creation_and_decoding():
    data = {"sub": "test@example.com", "extra_data": "something"}
    token = create_access_token(data)
    decoded_data = decode_token(token)
    assert decoded_data is not None
    assert decoded_data["sub"] == data["sub"]
    assert decoded_data["extra_data"] == data["extra_data"]
    assert "exp" in decoded_data

def test_decode_invalid_token():
    invalid_token = "this.is.not.a.valid.token"
    decoded_data = decode_token(invalid_token)
    assert decoded_data is None