@echo off
title Hermes School - Dashboard
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch-dashboard.ps1"
if errorlevel 1 pause
