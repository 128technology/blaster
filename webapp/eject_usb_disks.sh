for usb_drive in /dev/disk/by-path/*usb*; do
  USB_DEV=`readlink $usb_drive | xargs basename`
  echo "offline" > /sys/block/$USB_DEV/device/state
  echo "1" > /sys/block/$USB_DEV/device/delete
done
