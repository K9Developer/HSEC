import React, { useEffect, useLayoutEffect, useRef } from "react";
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
import { PiPolygonBold } from "react-icons/pi";
import { TbPolygonOff } from "react-icons/tb";
import showPopup from "../utils/Popupmanager";

// Add modal with email

let timeout: null | number = null;
const img = new Image();

const CameraViewer = () => {
    const { cameraId } = useParams();
    const [camera, setCamera] = React.useState<null | Camera>(null);
    const [showShare, setShowShare] = React.useState<boolean>(false);
    const [currentSourceUrl, setCurrentSourceUrl] = React.useState<string>("");
    const [shareEmail, setShareEmail] = React.useState<string>("");
    const [loadingShare, setLoadingShare] = React.useState<boolean>(false);
    const [recordingPolygon, setRecordingRedzone] = React.useState<boolean>(false);
    const [askSavePolygon, setAskSaveRedzone] = React.useState<boolean>(false);
    // const [imageWidth, setImageSize] = React.useState<{ width: number; height: number }>({ width: 0, height: 0 });
    const [imageWidth, setImageSize] = React.useState<number>(0);
    const [imageHeight, setImageHeight] = React.useState<number>(0);
    const [polygonPoints, setPolygonPoints] = React.useState<[number, number][]>([]);

    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const presetPolygonPoints = useRef<boolean>(false);
    const firstFrame = useRef<boolean>(true);
    let resizedCurrPoints = useRef<boolean>(false);
    const mac = useRef<string | null>(null);
    const navigate = useNavigate();
    // const [streaming, setStreaming] = React.useState<boolean>(false);

    const resizePolygonPoints = (points: [number, number][]) => {
        if (!canvasRef.current) return points;
        const rect = canvasRef.current.getBoundingClientRect();
        return points.map(point => [
            Math.round(point[0] * (rect.width / imageWidth)),
            Math.round(point[1] * (rect.height / imageHeight))
        ]);
    }

    useEffect(() => {
        if (!camera?.red_zone) return;
        // if (presetPolygonPoints?.current) return;
        if (camera?.red_zone && camera.red_zone.length > 0) {
            setPolygonPoints(camera.red_zone.map(point => [point[0], point[1]]));
            presetPolygonPoints.current = true;
        }
    }, [canvasRef, camera]);

    const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
        if (!recordingPolygon) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        resizedCurrPoints.current = true;
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        console.log("Canvas clicked at:", x, y);

        setPolygonPoints(prevPoints => {
            if (prevPoints.length === 0) return [[x, y]];

            const [firstX, firstY] = prevPoints[0];
            const dx = x - firstX;
            const dy = y - firstY;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < 10) {
                return prevPoints;
            }

            return [...prevPoints, [x, y]];
        });
    };

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) {
            console.error("Canvas element not found");
            return;
        }

        const ctx = canvas.getContext("2d");
        if (!ctx) {
            console.error("Failed to get canvas context");
            return;
        }

        console.log("Drawing polygon points:", polygonPoints);

        const rect = canvas.getBoundingClientRect();

        canvas.width = rect.width;
        canvas.height = rect.height;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (polygonPoints.length > 0) {
            ctx.beginPath();
            ctx.moveTo(polygonPoints[0][0], polygonPoints[0][1]);
            polygonPoints.forEach(point => {
                ctx.lineTo(point[0], point[1]);
            });
            ctx.closePath();
            ctx.fillStyle = "rgba(255, 0, 0, 0.07)";
            ctx.fill();

            ctx.strokeStyle = "rgba(255, 0, 0, 0.3)";
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.fillStyle = "rgba(255, 0, 0, 0.3)";
            polygonPoints.forEach(([x, y]) => {
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, Math.PI * 2);
                ctx.fill();
            });
        }
    }, [polygonPoints, canvasRef.current, imageWidth]);

    useLayoutEffect(() => {
        if (resizedCurrPoints.current) return;
        if (!canvasRef.current || polygonPoints.length === 0 || !imageWidth) return;
        console.log("Resizing polygon points due to image size change:", imageWidth, imageHeight);
        resizedCurrPoints.current = true;
        const newPoints = resizePolygonPoints(polygonPoints);
        setPolygonPoints(newPoints as any)
    }, [imageWidth, imageHeight, canvasRef.current, polygonPoints]);

    const onFrame = (data: any) => {
        if (timeout) clearTimeout(timeout);
        const newSourceUrl = `data:image/jpeg;base64,${data.frame}`;
        if (firstFrame.current) {
            console.log("Setting initial image size from new source URL");
            img.src = newSourceUrl;
            img.onload = () => {
                console.log("Image loaded:", img.width, img.height);
                setImageSize(img.width);
                setImageHeight(img.height);
            };
            firstFrame.current = false;
        }

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
            // setStreaming(true);
            let res = await DataManager.startStreamCamera(cameraData.mac);
            if (!res.success) {
                console.error("Failed to start camera stream:", res.info);
                showPopup("Failed to start camera stream: " + res.info, "error");
                navigate("/");
                return;
            }
            mac.current = cameraData.mac;
        } catch (error) {
            console.error("Error fetching camera data:", error);
            showPopup("Error fetching camera data: " + error.message, "error");
            navigate("/");
        }
    }

    useEffect(() => {
        // will fetch camera data from the server using cameraId
        DataManager.addEventListener("frame", onFrame);
        setupStream();

        timeout = setTimeout(() => {
            if (!camera || !currentSourceUrl) {
                showPopup("Failed to load camera feed. Please try again later.", "error");
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

            <Modal visible={askSavePolygon} onClose={() => setAskSaveRedzone(false)}>
                <p className="text-foreground text-sm">Do you want to save the polygon?</p>
                <div className="flex flex-row gap-2 mt-4">
                    <Button
                        text="Yes"
                        className="w-full"
                        onClick={() => {
                            // Save polygon logic here
                            setAskSaveRedzone(false);
                            const canvas = canvasRef.current;
                            if (!canvas) {
                                showPopup("Canvas not available. Please try again.", "error");
                                return;
                            }
                            const rect = canvas.getBoundingClientRect();
                            const resizedPoints = polygonPoints.map(point => {
                                return [
                                    Math.round(point[0] * (imageWidth / rect.width)),
                                    Math.round(point[1] * (imageHeight / rect.height))
                                ];
                            });

                            DataManager.saveRedzone(camera.mac, resizedPoints as any).then((res: any) => {
                                if (res.success) {
                                    showPopup("Polygon saved successfully!", "success");
                                    setRecordingRedzone(false);
                                } else showPopup("Failed to save polygon: " + res.info, "error");
                            })
                        }}
                    />
                    <Button
                        text="No"
                        className="w-full"
                        onClick={() => {
                            setAskSaveRedzone(false)
                            setPolygonPoints([]);
                        }}
                    />
                </div>
            </Modal>

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
                            showPopup("Please enter a valid email address.", "error");
                            return;
                        }
                        setLoadingShare(true);
                        DataManager.shareCamera(camera.mac, shareEmail)
                            .then((res: any) => {
                                setLoadingShare(false);
                                if (res.success) {
                                    showPopup("Camera shared successfully!", "success");
                                    setShowShare(false);
                                } else showPopup("Failed to share camera: " + res.info, "error");
                            })
                            .catch((err: any) => {
                                setLoadingShare(false);
                                console.error("Error sharing camera:", err);
                                showPopup("An error occurred while sharing the camera. Please try again later.", "error");
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
                    <div className="rounded-xl bg-lightpurple w-full relative" style={{
                        aspectRatio: imageWidth / imageHeight,
                    }}>
                        <img src={currentSourceUrl} alt="Camera Feed" className="w-full h-full" />
                        <canvas className="w-full absolute top-0 left-0 h-full rounded-md bg-transparent" id="cameraCanvas" ref={canvasRef} onClick={handleCanvasClick} />

                    </div>
                </div>
                <div className="w-full px-2 flex flex-row gap-2">
                    {/* <Button text="Share" className="w-1/2" icon={FaShareAlt} onClick={() => setShowShare(true)} /> */}
                    <Button text="Share" className="w-full" icon={FaShareAlt} onClick={() => setShowShare(true)} />
                    {recordingPolygon ? <Button text="Stop Recording" className="w-full" secondary icon={TbPolygonOff} onClick={() => {
                        setRecordingRedzone(false)
                        setAskSaveRedzone(true);
                    }} /> : <Button text="Record Redzone" className="w-full" icon={PiPolygonBold} onClick={() => {
                        setPolygonPoints([]);
                        setRecordingRedzone(true)
                    }} />}
                </div>
            </div>
        </div>
    );
};

export default CameraViewer;
