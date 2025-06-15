import React from 'react'
import type { HsecNotification } from '../types';

interface Props {
  notification: HsecNotification;
}

const NotificationCard = ({ notification }: Props) => {
  return (
    <div className='w-full bg-mediumpurple rounded-md p-2 flex flex-col gap-1'>
      <div className="flex flex-col gap-0">
        <p className='text-foreground font-semibold text-base'>{notification.title}</p>
        <p className='text-foreground-trans text-sm'>{notification.message}</p>
      </div>

      {notification.frame &&
        <img src={"data:image/jpeg;base64," + notification.frame} alt="Notification Frame" className='w-full h-40 object-cover rounded-md mt-2' />
      }

      <p className='text-foreground-trans text-xs mt-1'>{new Date(notification.timestamp * 1000).toLocaleString()}</p>

    </div>
  )
}

export default NotificationCard