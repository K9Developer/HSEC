import React, { useEffect, useRef } from 'react'
import { IconContext } from 'react-icons';
import { IoMdArrowRoundBack } from 'react-icons/io';
import { useParams } from 'react-router-dom';
import TimeScroll from '../components/TimeScroll';
import Button from '../components/Button';
import { FaCalendar } from "react-icons/fa";
import { Calendar } from "../components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { DataManager } from '../utils/DataManager';

interface Props { }


const PlaybackPage = () => {
    const { cameraId } = useParams();
    const [currentSourceUrl, setCurrentSourceUrl] = React.useState<string>("");
    const [calendarOpen, setCalendarOpen] = React.useState<boolean>(false);
    const [validDateRange, setValidDateRange] = React.useState({
        start: new Date(0, 0, 0, 0, 0, 0),
        end: new Date(0, 0, 0, 0, 0, 0),
    })
    const [changedDate, setChangedDate] = React.useState<Date>(
        validDateRange.end
    );

    useEffect(() => {
        if (!cameraId) {
            console.error("Camera ID is not provided");
            return;
        }

        if (validDateRange.start === validDateRange.end) {
            console.error("Valid date range is not set");
            return;
        }
        const fetchPlaybackData = async () => {

            // changedDate + 1 second
            const dateWithOffset = new Date(changedDate.getTime() + 1000);
            const playbackRes = await DataManager.getPlaybackChunk(cameraId || "", changedDate, dateWithOffset);
            console.log("Playback response:", playbackRes);
        }

        fetchPlaybackData();

    }, [changedDate]);

    useEffect(() => {
        if (!cameraId) {
            console.error("Camera ID is not provided");
            return;
        }
        const func = async () => {
            const res = await DataManager.getPlaybackRange(cameraId);
            if (res.success) {
                setValidDateRange({
                    start: res.start_date,
                    end: res.end_date,
                });
                setChangedDate(res.end_date);
            }
        }
        func()

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
                    <p className='text-foreground font-semibold text-lg'>Playback</p>
                </div>
            </div>

            <div className="mt-2 p-2 flex flex-col gap-4 max-w-screen">
                <div className="rounded-xl bg-lightpurple w-full relative rounded-md overflow-hidden" style={{
                    aspectRatio: 358 / 268,
                }}>
                    <video
                        className="w-full h-full object-cover"
                        controls
                        autoPlay
                        src={"data:video/mp4;base64," + currentSourceUrl}
                        onError={(e) => {
                            console.error("Error loading video:", e);
                            setCurrentSourceUrl(""); // Reset the source URL on error
                        }} />

                </div>

                <div className="flex flex-col gap-2 items-center">
                    <div className='p-1 px-3 bg-mediumpurple text-foreground font-bold rounded-md w-fit'>
                        {changedDate.toLocaleDateString()} {changedDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                    <div className='flex flex-row gap-1 w-full items-center justify-between max-w-full'>
                        <TimeScroll startDate={validDateRange.start} endDate={validDateRange.end} onChange={setChangedDate} className='w-[85%]' dateChange={changedDate} />

                        <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
                            <PopoverTrigger asChild>
                                <button className="aspect-square p-4 rounded-md bg-lightblue text-black flex items-center justify-center">
                                    <FaCalendar />
                                </button>
                            </PopoverTrigger>
                            <PopoverContent className='dark !border-none'>
                                <Calendar
                                    mode="single"
                                    selected={changedDate}
                                    onSelect={(date) => {
                                        setCalendarOpen(false);
                                        console.log("Selected date:", date);
                                        if (date) setChangedDate(date);
                                    }}
                                    defaultMonth={validDateRange.end}
                                    className='dark'
                                    disabled={(date) =>
                                        date < validDateRange.start || date > validDateRange.end
                                    }
                                />
                            </PopoverContent>
                        </Popover>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default PlaybackPage