"""Honor digital-resource privacy even for legacy local static-file URLs."""
from pathlib import PurePosixPath
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.concurrency import run_in_threadpool
from app.database import SessionLocal
from app.dependencies import get_current_user
from app.models.digital_resource import DigitalResource
from app.services.ebook_storage import authorize

class ProtectedUploads(StaticFiles):
    def __init__(self, *args, session_factory=SessionLocal, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_factory=session_factory

    def check_access(self, path, authorization, download=False):
        # StaticFiles normalizes path before get_response; compare the same local URL.
        url='/uploads/'+str(PurePosixPath(path.replace('\\','/'))).lstrip('/')
        with self.session_factory() as db:
            resources=db.query(DigitalResource).filter(DigitalResource.file_url==url).all()
            if not resources:
                if url.startswith('/uploads/ebooks/'):raise HTTPException(404,'PDF not found')
                return
            scheme,_,token=(authorization or '').partition(' ')
            credentials=HTTPAuthorizationCredentials(scheme=scheme,credentials=token) if token else None
            user=get_current_user(credentials,db)
            # Shared local files must satisfy every referencing record's restrictions.
            for resource in resources:
                authorize(resource,user)
                if download and not resource.download_allowed:raise HTTPException(403,'Downloads are disabled for this resource.')

    async def get_response(self,path,scope):
        request=Request(scope)
        await run_in_threadpool(self.check_access,path,request.headers.get('authorization'),request.query_params.get('download')=='true')
        response=await super().get_response(path,scope)
        response.headers['Cache-Control']='private, no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        return response
