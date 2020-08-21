from fastapi import HTTPException
from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT
)

from ..services import AuthService
from ..utils import build_response
from ..db import (
    MongoDB,
    get_client
)
from ..models.user_models import (
    User,
    OutUser,
    UpdateUser
)


class UserService:
    def __init__(self):
        super().__init__()
        self._db = MongoDB(get_client())
        self._auth_service = AuthService()

    async def create_new_user(self, user: User):
        user_dict: dict = user.dict()

        hashed_pwd = self._auth_service.hash_pwd(user_dict['password'])
        user_dict.update({'password': hashed_pwd})

        _ = await self._db.insert_user(user_dict)

        return await build_response(HTTP_201_CREATED, msg='New user created')

    async def get_current_user(self, token: str):
        user_dict: dict = await self._auth_service.check_active_token(token)
        user_dict.update({'id': str(user_dict.get('_id'))})

        return JSONResponse(
            status_code=HTTP_200_OK,
            content={
                'success': True,
                'payload': OutUser(**user_dict).dict()
            },
        )

    async def update_user(self, user: UpdateUser, token: str):
        current_data: dict = await self._auth_service.check_active_token(token)
        current_data.update({'id': str(current_data.get('_id'))})

        update_data = user.dict(exclude_unset=True)

        if update_data.get('password', None):
            hashed_pwd = self._auth_service.hash_pwd(update_data['password'])
            update_data.update({'password': hashed_pwd})

        current_user = UpdateUser(**current_data)
        update_user = current_user.copy(update=update_data)
        updated_user = await self._db.update_user(update_user.dict(), current_data['email'])

        updated_user.update({'id': str(updated_user['_id'])})

        return JSONResponse(
            status_code=HTTP_200_OK,
            content={
                'success': True,
                'payload': OutUser(**updated_user).dict()
            },
        )

    async def delete_user(self, token: str):
        user_dict: dict = await self._auth_service.check_active_token(token)
        user = await self._db.delete_user(user_dict['email'])

        if user:
            return await build_response(msg='Removed user successfully')

        raise HTTPException(
            status_code=HTTP_204_NO_CONTENT,
            detail='Remove user failed'
        )
