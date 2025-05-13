import React, { useEffect } from "react";
import { useParams } from "react-router-dom";
import type { Camera } from "../types";
import { BASE64 } from "./HomePage";
import { PuffLoader } from "react-spinners";
import { IoMdArrowRoundBack } from "react-icons/io";
import { IconContext } from "react-icons";

const CameraViewer = () => {
    const { cameraId } = useParams();
    const [camera, setCamera] = React.useState<null | Camera>(null);
    const imageRef = React.useRef<HTMLImageElement>(null);
    const currentUrl = React.useRef<string | null>(null);

    useEffect(() => {
        // will fetch camera data from the server using cameraId
        setCamera({
            id: "3",
            name: "Camera 3",
            last_frame: BASE64,
            ip: "10.100.102.5",
            mac: "00:00:00:00:00:03",
        } as Camera);

        /**
        const onFrame = (frame: Uint8Array) => {
            const blob = new Blob([frame], { type: "image/jpeg" });
            const url = URL.createObjectURL(blob);
            imageRef.current.src = url;

            if (currentUrl.current) URL.revokeObjectURL(currentUrl.current);
            currentUrl.current = url;
        };

        DataManager.addEventListener(DataEvent.FRAME, onFrame);
        return () => DataManager.removeEventListener(DataEvent.FRAME, onFrame);
        */
    }, []);

    if (!camera) {
        return (
            <div className="flex justify-center items-center h-full bg-bg">
                <PuffLoader color="#629584" />
            </div>
        );
    }

    return (
        <div className="flex flex-col bg-bg h-full">
            <div className="bg-primary p-4 flex justify-center items-center relative">
                <div className="flex flex-col justify-between items-center">
                    <p className="text-secondary font-bold">{camera.name}</p>
                    <p className="text-bg font-semibold">{camera.ip}</p>
                </div>
                <div className="absolute left-5" onClick={() => window.history.back()}>
                    <IconContext.Provider value={{ className: "text-secondary click-effect" }}>
                        <IoMdArrowRoundBack size={30} />{" "}
                    </IconContext.Provider>
                </div>
            </div>
            <div className="mt-2 p-2">
                <div className="rounded-xl bg-secondary w-full">
                    <img ref={imageRef} alt="Live Feed" />
                </div>
            </div>
        </div>
    );
};

export default CameraViewer;
