import React, { useEffect, useState } from "react";
import { IoMdAdd } from "react-icons/io";
import { MdAccountCircle } from "react-icons/md";
import { IconContext } from "react-icons/lib";
import type { Camera, User } from "../types";
import CameraCard from "../components/CameraCard";
import { Link, useNavigate } from "react-router-dom";
import { UserManager } from "../utils/AccountManager";
import { DataManager } from "../utils/DataManager";

export const BASE64 =
    "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";
const TMP_CAMERA_DATA: Camera[] = [
    {
        id: "1",
        name: "Camera 1",
        last_frame: BASE64,
        ip: "10.100.102.3",
        mac: "00:00:00:00:00:01",
    },
    {
        id: "2",
        name: "Camera 2",
        last_frame: BASE64,
        ip: "10.100.102.4",
        mac: "00:00:00:00:00:02",
    },
    {
        id: "3",
        name: "Camera 3",
        last_frame: BASE64,
        ip: "10.100.102.5",
        mac: "00:00:00:00:00:03",
    },
    {
        id: "4",
        name: "Camera 4",
        last_frame: BASE64,
        ip: "10.100.102.6",
        mac: "00:00:00:00:00:04",
    },
    {
        id: "5",
        name: "Camera 5",
        last_frame: BASE64,
        ip: "10.100.102.7",
        mac: "00:00:00:00:00:05",
    },
];

// TODO: Have some DataManager, for example DataManager.getCameras(), DataManager.login(), ...

const emailToName = (email?: string) => {
    if (!email) return "Guest";
    const name = email.split("@")[0];
    return name.charAt(0).toUpperCase() + name.slice(1);
};

const HomePage = () => {
    const navigate = useNavigate();
    const [cameraList, setCameraList] = useState<Camera[]>([]);
    const [currUser, setCurrUser] = useState<null | User>(null);

    useEffect(() => {
        // if (!DataManager.isConnected()) navigate("connect")

        setCameraList(TMP_CAMERA_DATA);
        setCurrUser(UserManager.getLocalUser());
    }, []);

    return (
        <div className="bg-darkpurple w-full h-full flex flex-col overflow-y-hidden">
            <div className="h-[93%] flex flex-col gap-5">
                <div className="flex justify-between h-15 items-center bg-mediumpurple p-3">
                    <p className="text-foreground text-lg font-semibold">{currUser?.logged_in ? `Welcome, ${emailToName(currUser?.email)}` : ""}</p>
                    <Link to="/account">
                        <IconContext.Provider value={{ className: "text-foreground" }}>
                            <MdAccountCircle size={40} />
                        </IconContext.Provider>
                    </Link>
                </div>
                <div className="flex flex-col gap-3 p-3 overflow-y-auto h-full">
                    {cameraList.length === 0 ? (
                        <div className="flex justify-center items-center h-full">
                            <p className="text-lighterpurple font-bold tracking-wide">No cameras available</p>
                        </div>
                    ) : !currUser?.logged_in ? (
                        <div className="flex justify-center items-center h-full">
                            <p className="text-lighterpurple font-bold tracking-wide">Please log in to see the cameras</p>
                        </div>
                    ) : (
                        cameraList.map((camera) => (
                            <CameraCard
                                key={camera.id}
                                camera={camera}
                                onClick={() => {
                                    console.log("view", camera.id)
                                    navigate(`camera/${camera.id}`)
                                }}
                            />
                        ))
                    )}
                </div>
            </div>
            <div className="h-[7%] bg-mediumpurple relative flex items-center justify-center">
                <Link to={!currUser?.logged_in ? "/" : "discover"}>
                    <div
                        className={
                            "bg-lightblue cursor-pointer w-14 aspect-square rounded-full mb-14 flex justify-center items-center  " +
                            (currUser?.logged_in ? " click-effect" : "")
                        }
                    >
                        <IconContext.Provider value={{ className: `${currUser?.logged_in ? "text-darkpurple" : "text-lightpurple"}` }}>
                            <IoMdAdd size={25} />
                        </IconContext.Provider>
                    </div>
                </Link>
            </div>
        </div>
    );
};

export default HomePage;
