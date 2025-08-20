set path=%path%;C:\Program Files (x86)\Opera\;"C:\Program Files (x86)\Google\Chrome\Application\"

git pull

@echo off

tasklist|findstr "python" >myfile.txt

set "filemask=myfile.txt"
for %%A in (%filemask%) do if %%~zA==0 (
echo No Earlier Running Instance Found
@start /b cmd /c chrome http://localhost:8080/
python manage.py runserver 0.0.0.0:8080
) ELSE (
echo Shutting the Earlier Running Instance
taskkill /IM python.exe /F
@start /b cmd /c chrome http://localhost:8080/
python manage.py runserver 0.0.0.0:8080
)
