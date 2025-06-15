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
import { PiPolygonBold } from "react-icons/pi";
import { TbPolygonOff } from "react-icons/tb";
import { BiStopCircle } from "react-icons/bi";

// Add modal with email

let timeout: null | number = null;
const img = new Image();
let firstFrame = true;

const CameraViewer = () => {
    const { cameraId } = useParams();
    const [camera, setCamera] = React.useState<null | Camera>(null);
    const [showShare, setShowShare] = React.useState<boolean>(false);
    const [currentSourceUrl, setCurrentSourceUrl] = React.useState<string>("");
    const [shareEmail, setShareEmail] = React.useState<string>("");
    const [loadingShare, setLoadingShare] = React.useState<boolean>(false);
    const [recordingPolygon, setRecordingPolygon] = React.useState<boolean>(false);
    const [askSavePolygon, setAskSavePolygon] = React.useState<boolean>(false);
    const [imageSize, setImageSize] = React.useState<{ width: number; height: number }>({ width: 0, height: 0 });
    const [polygonPoints, setPolygonPoints] = React.useState<[number, number][]>([]);

    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const presetPolygonPoints = useRef<boolean>(false);
    const mac = useRef<string | null>(null);
    const navigate = useNavigate();
    // const [streaming, setStreaming] = React.useState<boolean>(false);

    useEffect(() => {
        if (!camera?.red_zone) return;
        // if (presetPolygonPoints?.current) return;
        console.log(camera?.red_zone, camera.red_zone.length)
        if (camera?.red_zone && camera.red_zone.length > 0) {
            console.log(camera.red_zone)
            setPolygonPoints(camera.red_zone.map(point => [point[0], point[1]]));
            presetPolygonPoints.current = true;
        }
    }, [canvasRef, camera]);

    const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
        if (!recordingPolygon) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

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
        console.log("Canvas points updated:", polygonPoints);
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
    }, [polygonPoints, canvasRef.current, imageSize]);


    const onFrame = (data: any) => {
        if (timeout) clearTimeout(timeout);
        const newSourceUrl = `data:image/jpeg;base64,${data.frame}`;
        if (firstFrame) {
            console.log("Setting initial image size from new source URL");
            img.src = newSourceUrl;
            img.onload = () => {
                setImageSize({ width: img.width, height: img.height });
            };
            firstFrame = false;
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

            <Modal visible={askSavePolygon} onClose={() => setAskSavePolygon(false)}>
                <p className="text-foreground text-sm">Do you want to save the polygon?</p>
                <div className="flex flex-row gap-2 mt-4">
                    <Button
                        text="Yes"
                        className="w-full"
                        onClick={() => {
                            // Save polygon logic here
                            setAskSavePolygon(false);
                            DataManager.savePolygon(camera.mac, polygonPoints).then((res: any) => {
                                if (res.success) {
                                    alert("Polygon saved successfully!");
                                    setPolygonPoints([]);
                                    setRecordingPolygon(false);
                                } else {
                                    alert("Failed to save polygon: " + res.info);
                                }
                            })
                        }}
                    />
                    <Button
                        text="No"
                        className="w-full"
                        onClick={() => {
                            setAskSavePolygon(false)
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
                    <div className="rounded-xl bg-lightpurple w-full relative" style={{
                        aspectRatio: imageSize.width / imageSize.height,
                    }}>
                        <img src={currentSourceUrl} alt="Camera Feed" className="w-full h-full" />
                        <canvas className="w-full absolute top-0 left-0 h-full rounded-md bg-transparent" id="cameraCanvas" ref={canvasRef} onClick={handleCanvasClick} />

                    </div>
                </div>
                <div className="w-full px-2 flex flex-row gap-2">
                    {/* <Button text="Share" className="w-1/2" icon={FaShareAlt} onClick={() => setShowShare(true)} /> */}
                    <Button text="Share" className="w-full" icon={FaShareAlt} onClick={() => setShowShare(true)} />
                    {recordingPolygon ? <Button text="Stop Polygon" className="w-full" icon={TbPolygonOff} onClick={() => {
                        setRecordingPolygon(false)
                        setAskSavePolygon(true);
                    }} /> : <Button text="Record Polygon" className="w-full" icon={PiPolygonBold} onClick={() => {
                        setPolygonPoints([]);
                        setRecordingPolygon(true)
                    }} />}
                </div>
            </div>
        </div>
    );
};

export default CameraViewer;
