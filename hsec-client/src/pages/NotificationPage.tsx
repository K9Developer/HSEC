import React, { useContext, useEffect } from 'react'
import { IconContext } from 'react-icons'
import { IoMdArrowRoundBack } from 'react-icons/io'
import UserContext from '../contexts/UserContext';
import NotificationCard from '../components/NotificationCard';
import { DataManager } from '../utils/DataManager';
import type { HsecNotification } from '../types';

const NotificationPage = () => {
    const { user, setUser } = useContext(UserContext);
    const [notifications, setNotifications] = React.useState<HsecNotification[]>([]);


    useEffect(() => {
        // get notifs
        DataManager.getNotifications().then((notifs) => {
            if (notifs.success) {
                const n = notifs.notifications
                n.reverse(); 
                setNotifications(n);
            } else {
                console.error("Failed to fetch notifications:", notifs.info);
            }
        })
    }, []);

    return (
        <div className="flex flex-col h-full bg-darkpurple relative">
            <div className="sticky w-full top-0 p-3 bg-mediumpurple">
                <div className="flex relative justify-center items-center" onClick={() => window.history.back()}>
                    <div className='flex items-center h-full absolute left-0'>
                    <IconContext.Provider value={{ className: "text-foreground" }}>
                        <IoMdArrowRoundBack size={30} />
                    </IconContext.Provider>
                    </div>
                    <p className='text-foreground font-semibold text-lg'>Alerts</p>
                </div>
                
            </div>

            <div className='overflow-y-auto w-full flex flex-col justify-start gap-3 p-2 pb-0'>
                {notifications.map(notif => <NotificationCard notification={notif}/>)}
            </div>
        </div>
    )
}

export default NotificationPage