# beedev-portal

requirements.txt contains all current packages needed as of 9/29/25
pip freeze > requirements.txt (to create/update file)

To update your env with the required packages run:
pip install -r requirements.txt

# Updates:
## As of 10/29/25:
On new deployment
- Check if new migrations are needed
- Check server .env file (update date should match drive env)
- If updating env change db server setting to production, Proposal url to live vs local, swap debug to false
- on settings file update proposal parts section to live vs local
- On client live deploy (when there) change logout redirect to live vs /


# On Mac weasyPrint may cause run issues:
brew update
brew install pkg-config cairo pango gdk-pixbuf libffi harfbuzz fribidi
or
brew install glib pango cairo gobject-introspection gdk-pixbuf libffi

gdk-pixbuf-query-loaders --update-cache || true
# (optional but harmless)
brew install libpng jpeg libxml2
pip install -U --force-reinstall weasyprint cairocffi



# May need to install the following for deployment:
sudo apt-get update
sudo apt-get install -y libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi8 libxml2 libjpeg62-turbo libpng16-16 fonts-dejavu-core


# If you keep running into errors when starting server try the following (MAC):
brew --prefix glib
# expect: /opt/homebrew/opt/glib

ls -l /opt/homebrew/opt/glib/lib/libgobject-2.0*.dylib
# you should see libgobject-2.0.dylib (and usually libgobject-2.0.0.dylib)

export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/opt/glib/lib:/opt/homebrew/lib:${DYLD_FALLBACK_LIBRARY_PATH}"
export GI_TYPELIB_PATH="/opt/homebrew/lib/girepository-1.0:${GI_TYPELIB_PATH}"

python -c "import os; print('DYLD_FALLBACK_LIBRARY_PATH=',os.environ.get('DYLD_FALLBACK_LIBRARY_PATH')); from ctypes.util import find_library as f; print('find_library:', f('gobject-2.0'))"

As long as you don't see None after this do the following:
start the env
then enter
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/opt/glib/lib:/opt/homebrew/lib:${DYLD_FALLBACK_LIBRARY_PATH}"
export GI_TYPELIB_PATH="/opt/homebrew/lib/girepository-1.0:${GI_TYPELIB_PATH}"
then
deactivate 2>/dev/null || true
and restart the env