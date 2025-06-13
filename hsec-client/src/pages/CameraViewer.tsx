import React, { useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { Camera } from "../types";
import { PuffLoader } from "react-spinners";
import { IoMdArrowRoundBack } from "react-icons/io";
import { IconContext } from "react-icons";
import { DataManager } from "../utils/DataManager";
import Button from "../components/Button";
import { FaShareAlt } from "react-icons/fa";
import Modal from "../components/Modal";
import Input from "../components/Input";


// Add modal with email

let timeout: null | number = null;
const CameraViewer = () => {
    const { cameraId } = useParams();
    const [camera, setCamera] = React.useState<null | Camera>(null);
    const [showShare, setShowShare] = React.useState<boolean>(false);
    const [currentSourceUrl, setCurrentSourceUrl] = React.useState<string>("");
    const [shareEmail, setShareEmail] = React.useState<string>("");
    const [loadingShare, setLoadingShare] = React.useState<boolean>(false);
    const mac = useRef<string | null>(null);
    const navigate = useNavigate();
    // const [streaming, setStreaming] = React.useState<boolean>(false);

    const onFrame = (data: any) => {
        if (timeout) clearTimeout(timeout);
        console.log("Received frame from camera:", cameraId);
        const newSourceUrl = `data:image/jpeg;base64,${data.frame}`;
        setCurrentSourceUrl(newSourceUrl);
    };


    const setupStream = async () => {
        // if (streaming) {
        //     console.warn("Stream is already active");
        //     return;
        // }
        if (!cameraId) {
            console.error("Camera ID is not provided");
            return;
        }

        const macAddr = cameraId.match(/.{1,2}/g)?.join(":").toUpperCase();
        if (!macAddr) {
            console.error("Invalid camera ID format");
            return;
        }

        try {
            const camerasData = await DataManager.getCameras();
            const cameraData = camerasData.cameras.find((cam: Camera) => cam.mac.toUpperCase() === macAddr);
            if (!cameraData) {
                console.error("Camera not found");
                return;
            }
            setCamera(cameraData);
            console.log("Camera data (start):", cameraData);
            // setStreaming(true);
            let res = await DataManager.startStreamCamera(cameraData.mac);
            if (!res.success) {
                console.error("Failed to start camera stream:", res.info);
                alert("Failed to start camera stream: " + res.info);
                navigate("/");
                return;
            }
            mac.current = cameraData.mac;
        } catch (error) {
            console.error("Error fetching camera data:", error);
            alert("Failed to fetch camera data. Please try again later.");
            navigate("/");
        }
    }

    useEffect(() => {
        // will fetch camera data from the server using cameraId
        DataManager.addEventListener("frame", onFrame);
        setupStream();

           timeout = setTimeout(() => {
                if (!camera || !currentSourceUrl) {
                    alert("Failed to load camera feed. Please try again later.");
                    navigate("/");
                }
            }, 5000);

        return () => {
            DataManager.stopStreamCamera(mac.current!);
            DataManager.removeEventListener("frame");
            if (timeout) clearTimeout(timeout);
        }
    }, []);

    if (!camera || !currentSourceUrl) {
        return (
            <div className="flex justify-center items-center h-full bg-darkpurple">
                <PuffLoader color="#D1CCE0" />
            </div>
        );
    }

    return (
        <div className="flex flex-col bg-darkpurple h-full">

            <Modal
                visible={showShare}
                onClose={() => setShowShare(false)}
                showCloseButton={true}
            >

                <p className="text-foreground text-sm">Please enter the email of the person you want to share the camera to</p>
                <Input placeholder="Email" onChange={(val: string) => {
                    setShareEmail(val);
                    return true;
                }} pattern={/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/} />
                <Button
                    text="Share"
                    className="mt-8 w-full"
                    isLoading={loadingShare}
                    onClick={() => {
                        if (!shareEmail) {
                            alert("Please enter a valid email address.");
                            return;
                        }
                        setLoadingShare(true);
                        DataManager.shareCamera(camera.mac, shareEmail)
                            .then((res: any) => {
                                setLoadingShare(false);
                                if (res.success) {
                                    alert("Camera shared successfully!");
                                    setShowShare(false);
                                } else {
                                    alert("Failed to share camera: " + res.info);
                                }
                            })
                            .catch((err: any) => {
                                setLoadingShare(false);
                                console.error("Error sharing camera:", err);
                                alert("An error occurred while sharing the camera. Please try again later.");
                            });
                    }}
                />

            </Modal>

            <div className="bg-mediumpurple p-4 flex justify-center items-center relative">
                <div className="flex flex-col justify-between items-center">
                    <p className="text-foreground font-bold">{camera.name}</p>
                    <p className="text-lighterpurple font-semibold">{camera.ip}</p>
                </div>
                <div className="absolute left-5" onClick={() => window.history.back()}>
                    <IconContext.Provider value={{ className: "text-foreground" }}>
                        <IoMdArrowRoundBack size={30} />
                    </IconContext.Provider>
                </div>
            </div>
            <div className="flex flex-col justify-between h-full pb-4 px-2">
                <div className="mt-2 p-2">
                    <div className="rounded-xl bg-lightpurple w-full">
                        <img src={currentSourceUrl ? currentSourceUrl : undefined} alt="Live Feed" />
                    </div>
                </div>
                <div className="w-full px-2 flex flex-row gap-2">
                    {/* <Button text="Share" className="w-1/2" icon={FaShareAlt} onClick={() => setShowShare(true)} /> */}
                    <Button text="Share" className="w-full" icon={FaShareAlt} onClick={() => setShowShare(true)} />
                </div>
            </div>
        </div>
    );
};

export default CameraViewer;
