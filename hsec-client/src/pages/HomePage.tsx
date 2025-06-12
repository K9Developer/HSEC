import { useContext, useEffect, useState } from "react";
import { IoMdAdd } from "react-icons/io";
import { MdAccountCircle } from "react-icons/md";
import { IconContext } from "react-icons/lib";
import type { Camera } from "../types";
import CameraCard from "../components/CameraCard";
import { Link, useNavigate } from "react-router-dom";
import { UserManager } from "../utils/AccountManager";
import { DataManager } from "../utils/DataManager";
import { macToId } from "../utils";
import UserContext from "../contexts/UserContext";

// TODO: Make the servercode be saved, if connection unsuccessful, show a modal to enter the server code
// TODO: When at some point theres a disconnect, show a modal to enter the server code again
// TODO: Add password hashing
// TODO: Have some DataManager, for example DataManager.getCameras(), DataManager.login(), ...

const emailToName = (email?: string) => {
    if (!email) return "Guest";
    const name = email.split("@")[0];
    return name.charAt(0).toUpperCase() + name.slice(1);
};

let cameraGetInterval: number | null = null;
const HomePage = () => {
    const { user, setUser } = useContext(UserContext);

    const navigate = useNavigate();
    const [cameraList, setCameraList] = useState<Camera[]>([]);


    const getCameras = async () => {
        if (!user?.logged_in || !DataManager.isConnected()) {
            console.log(user)
            console.warn("User not logged in or not connected to server, skipping camera fetch.");
            setCameraList([]);
            return;
        }
        try {
            const cameras = await DataManager.getCameras();
            setCameraList(cameras.cameras || []);
        } catch (error) {
            console.error("Failed to fetch cameras:", error);
        }
    }

    useEffect(() => {
        if (cameraGetInterval) clearInterval(cameraGetInterval);
        if (user && user.logged_in) {
            cameraGetInterval = setInterval(() => {
                console.log("Refreshing camera list...");
                getCameras();
            }, 1000); // Refresh every 5 seconds
        }
        getCameras();
        return () => {if (cameraGetInterval) clearInterval(cameraGetInterval);}
    }, [user])

    useEffect(() => {
        // const interval = setInterval(() => {
        //     console.log("Refreshing camera list...");
        //     getCameras();
        // }, 30000); // Refresh every 5 seconds
        // getCameras();
        // return () => clearInterval(interval);
    }, [])


    return (
        <div className="bg-darkpurple w-full h-full flex flex-col overflow-y-hidden">

            <div className="h-[93%] flex flex-col gap-5">
                <div className="flex justify-between h-15 items-center bg-mediumpurple p-3">
                    <p className="text-foreground text-lg font-semibold">{user?.logged_in ? `Welcome, ${emailToName(user?.email)}` : ""}</p>
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
                    ) : !user?.logged_in ? (
                        <div className="flex justify-center items-center h-full">
                            <p className="text-lighterpurple font-bold tracking-wide">Please log in to see the cameras</p>
                        </div>
                    ) : (
                        cameraList.map((camera) => (
                            <CameraCard
                                key={camera.mac}
                                camera={camera}
                                onClick={() => {
                                    navigate(`camera/${macToId(camera.mac)}`);
                                }}
                                updateCameraList={() => getCameras()}
                            />
                        ))
                    )}
                </div>
            </div>
            <div className="h-[7%] bg-mediumpurple relative flex items-center justify-center">
                <Link to={!user?.logged_in ? "/" : "discover"}>
                    <div
                        className={
                            "bg-lightblue cursor-pointer w-14 aspect-square rounded-full mb-14 flex justify-center items-center  " +
                            (user?.logged_in ? " click-effect" : "")
                        }
                    >
                        <IconContext.Provider value={{ className: `${user?.logged_in ? "text-darkpurple" : "text-lightpurple"}` }}>
                            <IoMdAdd size={25} />
                        </IconContext.Provider>
                    </div>
                </Link>
            </div>
        </div>
    );
};

export default HomePage;
