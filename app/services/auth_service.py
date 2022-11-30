import hashlib
import jwt

from fastapi import HTTPException
from jwt import PyJWTError
from fastapi.param_functions import Body
from starlette.responses import JSONResponse
from passlib.context import CryptContext

from datetime import (
    datetime,
    timedelta
)

from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED
)

from ..utils import build_response

from ..db import (
    get_client,
    MongoDB
)

from ..configs import (
    ACCESS_TOKEN_EXP,
    REFRESH_TOKEN_EXP,
    SECRET_KEY,
    ALGORITHM
)

from ..models import (
    LoginUser,
    OutUser
)


class AuthService:
    def __init__(self):
        super().__init__()
        self._db = MongoDB(get_client())
        self._myctx = CryptContext(schemes=['sha256_crypt'], deprecated='auto')
        self._access_token_exp = ACCESS_TOKEN_EXP
        self._refresh_token_exp = REFRESH_TOKEN_EXP
        self._algo = ALGORITHM
        self._secret = SECRET_KEY

    def hash_pwd(self, pwd: str):
        return self._myctx.hash(pwd)

    async def check_active_token(self, token: str):
        usr: dict = self._decode_token(token)

        user_dict = await self._db.get_user(usr['usr'])
        if not user_dict:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail='Invalid token',
                headers={'Authenticate': 'Bearer'}
            )

        return user_dict

    async def generate_access_token(self, user: LoginUser = Body(None, embed=True), grant_type: str = Body(...), refresh_token: str = Body(None)):
        if grant_type == 'password' and user is not None:
            response = await self._login_for_access_token(user)
            return response

        if grant_type == 'refresh_token' and refresh_token is not None:
            usr: dict = self._decode_token(refresh_token)

            if usr['token_type'] == 'refresh':
                access_token_expires = timedelta(
                    minutes=self._access_token_exp)
                payload = {
                    'id': str(usr.get('id')),
                    'usr': usr.get('usr')
                }

                access, refresh = await self._create_jwt_token(payload, access_token_expires)

                return JSONResponse(
                    status_code=HTTP_200_OK,
                    content={
                        'token_type': 'bearer',
                        'access_token': access.decode('utf-8'),
                        'expires_in': self._access_token_exp,
                        'refresh_token': refresh.decode('utf-8')
                    }
                )

        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail='Invalid grant type or token',
            headers={'Authenticate': 'Bearer'}
        )

    async def validate_token(self, token: str):
        user_dict: dict = await self.check_active_token(token)
        user_dict.update({'id': str(user_dict.get('_id'))})
        return await build_response(data=OutUser(**user_dict).dict())

    async def _login_for_access_token(self, user: LoginUser):
        user_dict = user.dict()

        usr = await self._db.get_user(user_dict['email'])
        if not usr:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail='Incorrect email or password',
                headers={'Authenticate': 'Bearer'}
            )

        v = self._verify_pwd(user_dict['password'], usr['password'])
        if not v:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail='Incorrect email or password',
                headers={'Authenticate': 'Bearer'}
            )

        access_token_expires = timedelta(minutes=self._access_token_exp)
        payload = {
            'id': str(usr.get('id')),
            'usr': usr.get('email')
        }

        access, refresh = await self._create_jwt_token(payload, access_token_expires)

        return JSONResponse(
            status_code=HTTP_200_OK,
            content={
                'token_type': 'bearer',
                'access_token': access,
                'expires_in': self._access_token_exp,
                'refresh_token': refresh
            }
        )

    def _verify_pwd(self, plain_pwd: str, hashed_pwd: str):
        return self._myctx.verify(plain_pwd, hashed_pwd)

    async def _create_jwt_token(self, data: dict, exp_delta: timedelta = None):
        access_token = self._gen_access_token(data, exp_delta)
        refresh_token = self._gen_refresh_token(data)

        return access_token, refresh_token

    def _decode_token(self, token: str):
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algo])
            usr: str = payload.get('usr')
            if usr is None:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail='Invalid token',
                    headers={'Authenticate': 'Bearer'},
                )
            return payload
        except PyJWTError:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail='Token is not active',
                headers={'Authenticate': 'Bearer'},
            )

    def _gen_access_token(self, data: dict, exp_delta: timedelta = None):
        to_encode = data.copy()
        if exp_delta:
            expire = datetime.utcnow() + exp_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self._access_token_exp)

        to_encode.update({'token_type': 'access'})
        to_encode.update({'exp': expire})

        encoded_jwt = jwt.encode(to_encode, self._secret, algorithm=self._algo)
        return encoded_jwt

    def _gen_refresh_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self._refresh_token_exp)

        to_encode.update({'token_type': 'refresh'})
        to_encode.update({'exp': expire})

        encoded_jwt = jwt.encode(to_encode, self._secret, algorithm=self._algo)
        return encoded_jwt
