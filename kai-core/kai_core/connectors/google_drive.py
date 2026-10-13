from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from kai_core.config import SETTINGS


class ConnectorSecurityError(ValueError):
    pass


@dataclass
class GoogleDriveConnector:
    base_url: str = SETTINGS.drive_connector_url
    token: str = SETTINGS.drive_connector_token
    timeout: int = SETTINGS.drive_connector_timeout

    def _call(self, method: str, **params):
        if not self.base_url:
            return {"ok": False, "error": "KAI_DRIVE_CONNECTOR_URL not configured", "method": method, "params": params}

        payload = json.dumps({"method": method, "params": params}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = Request(self.base_url, data=payload, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            return {"ok": False, "error": f"HTTP {exc.code}", "method": method}

    @staticmethod
    def _require_write_guards(params: dict, *, admin: bool = False, needs_hash: bool = False) -> None:
        if params.get("createBackup") is not True:
            raise ConnectorSecurityError("createBackup=true es obligatorio")
        if params.get("asierApproved") is not True:
            raise ConnectorSecurityError("asierApproved=true es obligatorio")
        if admin and params.get("adminApproved") is not True:
            raise ConnectorSecurityError("adminApproved=true es obligatorio para acciones admin")
        if needs_hash and not params.get("expectedSha256"):
            raise ConnectorSecurityError("expectedSha256 es obligatorio para texto/código")

    def healthCheck(self):
        return self._call("healthCheck")

    def scanFolder(self, folderId: str, recursive: bool = True):
        return self._call("scanFolder", folderId=folderId, recursive=recursive)

    def readFileText(self, fileId: str):
        return self._call("readFileText", fileId=fileId)

    def readManyFilesText(self, fileIds: list[str]):
        return self._call("readManyFilesText", fileIds=fileIds)

    def getFileTextHash(self, fileId: str):
        return self._call("getFileTextHash", fileId=fileId)

    def appendToGoogleDoc(self, **params):
        self._require_write_guards(params, needs_hash=True)
        return self._call("appendToGoogleDoc", **params)

    def insertTextAfterMarker(self, **params):
        self._require_write_guards(params, needs_hash=True)
        return self._call("insertTextAfterMarker", **params)

    def replaceInGoogleDoc(self, **params):
        self._require_write_guards(params, needs_hash=True)
        return self._call("replaceInGoogleDoc", **params)

    def createTextFileInFolder(self, **params):
        self._require_write_guards(params, needs_hash=True)
        return self._call("createTextFileInFolder", **params)

    def writeTextFileWithBackup(self, **params):
        self._require_write_guards(params, needs_hash=True)
        return self._call("writeTextFileWithBackup", **params)

    def replaceInTextFile(self, **params):
        self._require_write_guards(params, needs_hash=True)
        return self._call("replaceInTextFile", **params)

    def ensureKnowledgeBase(self, **params):
        self._require_write_guards(params)
        return self._call("ensureKnowledgeBase", **params)

    def getKnowledgeBase(self, **params):
        return self._call("getKnowledgeBase", **params)

    def appendKnowledge(self, **params):
        self._require_write_guards(params)
        return self._call("appendKnowledge", **params)

    def searchKnowledge(self, **params):
        return self._call("searchKnowledge", **params)

    def moveToCompleteExtraction(self, **params):
        self._require_write_guards(params)
        return self._call("moveToCompleteExtraction", **params)

    def getAppsScriptContentHash(self, **params):
        return self._call("getAppsScriptContentHash", **params)

    def readAppsScriptContent(self, **params):
        return self._call("readAppsScriptContent", **params)

    def dryRunUpdateAppsScriptContent(self, **params):
        self._require_write_guards(params, admin=True, needs_hash=True)
        return self._call("dryRunUpdateAppsScriptContent", **params)

    def updateAppsScriptContent(self, **params):
        self._require_write_guards(params, admin=True, needs_hash=True)
        return self._call("updateAppsScriptContent", **params)

    def createAppsScriptVersion(self, **params):
        self._require_write_guards(params, admin=True)
        return self._call("createAppsScriptVersion", **params)

    def listAppsScriptDeployments(self, **params):
        return self._call("listAppsScriptDeployments", **params)

    def updateAppsScriptDeployment(self, **params):
        self._require_write_guards(params, admin=True)
        return self._call("updateAppsScriptDeployment", **params)
