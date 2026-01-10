@echo off
nssm install MSM "C:\Path\To\Python\python.exe" "-m msm_core.cli web start"
nssm set MSM AppDirectory "C:\Path\To\MSM"
nssm set MSM AppStdout "C:\Path\To\MSM\logs\service.log"
nssm set MSM AppStderr "C:\Path\To\MSM\logs\service.log"
nssm start MSM
