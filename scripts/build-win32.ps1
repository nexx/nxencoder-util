cd ..
& env\Scripts\Activate.ps1
cd nxencoder
pyinstaller --onefile --add-data 'resources/icon.svg;resources' --name 'nxecnoder-util' --icon 'resources/icon_bg.ico' __main__.pyw
