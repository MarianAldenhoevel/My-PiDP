@echo off
del %1.lst
del %1.obj
macro11.exe -l %1.lst -o %1.obj %1.mac
type %1.lst | python lsttosimh.py > %1.simh

dir %1.*
