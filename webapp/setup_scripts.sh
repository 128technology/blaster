###############################################################################
#
# Check for the presence of both a pre- and post-bootstrap script on the 
# install medium and if found, stage on the system being installed
#
# This is a snippet intended to be included in a kickstart file
# - Uses $INSTALLER_FILES
# - Uses $INSTALLER_ROOT
#
###############################################################################
if [ -f $INSTALLER_FILES/pre-bootstrap ]; then
  echo "Found pre-bootstrap script on install root, staging on system..."
  cp -f $INSTALLER_FILES/pre-bootstrap $INSTALLED_ROOT/etc/128technology/pre-bootstrap
else
  echo "Did not find pre-bootstrap script on install root"
fi
if [ -f $INSTALLER_FILES/post-bootstrap ]; then
  echo "Found post-bootstrap script on install root, staging on system..."
  cp -f $INSTALLER_FILES/post-bootstrap $INSTALLED_ROOT/etc/128technology/post-bootstrap
else
  echo "Did not find post-bootstrap script on install root"
fi
