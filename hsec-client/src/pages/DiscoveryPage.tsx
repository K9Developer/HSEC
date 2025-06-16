import React, { useEffect } from "react";
import { IconContext } from "react-icons";
import { IoMdArrowRoundBack } from "react-icons/io";
import { BeatLoader } from "react-spinners";
import { DataManager } from "../utils/DataManager";
import { BiSolidCctv } from "react-icons/bi";
import Modal from "../components/Modal";
import Input from "../components/Input";
import Button from "../components/Button";
import { useNavigate } from "react-router-dom";
import showPopup from "../utils/Popupmanager";

interface CameraDiscoveredType {
    ip: string;
    mac: string;
    port: number;
}

interface CameraConnectModal {
    camera: CameraDiscoveredType | null;
    show: boolean;
}

let connectTimeout: number | null = null;
const DiscoveryPage = () => {
    const [currCameraCode, setCurrCameraCode] = React.useState("");
    const [cameras, setCameras] = React.useState<{[mac: string]: CameraDiscoveredType}>({});
    const [cameraConnectModal, setCameraConnectModal] = React.useState<CameraConnectModal>({
        camera: null,
        show: false,
    });
    const [expectingCameraPair, setExpectingCameraPair] = React.useState(false);
    const navigate = useNavigate();

    const onCameraPairSuccess = (data: any) => {
        console.log("Camera Pair Success", data);
        setExpectingCameraPair(false);
        navigate("/");
        setCameraConnectModal({ camera: null, show: false });
        clearTimeout(connectTimeout!);
        // Handle camera pairing success
    };

    const onCameraPairFailure = (data: any) => {
        clearTimeout(connectTimeout!);
        setExpectingCameraPair(false);
        setCameraConnectModal({ camera: null, show: false });
        showPopup("Failed to pair camera: " + data.info, "error");
        // Handle camera pairing failure
    };

    const onCameraDiscovered = ({ ip, mac, port }: CameraDiscoveredType) => {
        console.log("Camera Discovered", ip, mac, cameras);
        setCameras((prevCameras) => ({
            ...prevCameras,
            [mac]: { ip, mac, port },
        }));

    };

    const attemptCameraConnect = (camera: CameraDiscoveredType | null, code: string) => {
        if (!camera) return;
        setExpectingCameraPair(true);
        DataManager.pairCamera(camera.ip, camera.port, camera.mac, code).then(
            (data) => {
                if (data.success) {
                    onCameraPairSuccess(data);
                } else {
                    onCameraPairFailure(data);
                }
            })
        // DataManager.connectToCamera(camera.ip, code);
    };

    useEffect(() => {
        DataManager.addEventListener("camera_discovered", onCameraDiscovered);
        DataManager.startDiscoverCameras();
        return () => {
            DataManager.stopDiscoverCameras();
            DataManager.removeEventListener("camera_discovered");
            if (connectTimeout) {
                clearTimeout(connectTimeout);
            }
        };
    }, []);

    return (
        <div className="flex justify-center h-full bg-darkpurple flex-col">
            <Modal visible={cameraConnectModal.show} onClose={() => setCameraConnectModal({ camera: null, show: false })}>
                <p className="text-foreground text-sm">Please enter the code written on the camera</p>
                <p className="text-lighterpurple text-xs mb-6">Attempting to connect to camera {cameraConnectModal.camera?.mac}</p>
                <Input placeholder="Camera Code" onChange={(val: string) => setCurrCameraCode(val)} disabled={expectingCameraPair} />
                <Button
                    text="Connect"
                    className="mt-8 w-full"
                    isLoading={expectingCameraPair}
                    onClick={() => {
                        if (!cameraConnectModal.camera) return;
                        console.log("Attempting to connect to camera", cameraConnectModal.camera.ip, currCameraCode);
                        attemptCameraConnect(cameraConnectModal.camera, currCameraCode);
                    }}
                />
            </Modal>

            <div className="w-full mb-5">
                <div className="p-3 bg-mediumpurple" onClick={() => window.history.back()}>
                    <IconContext.Provider value={{ className: "text-foreground" }}>
                        <IoMdArrowRoundBack size={30} />
                    </IconContext.Provider>
                </div>
            </div>
            <div className="flex flex-col gap-3 justify-start h-full mt-2 px-4">
                {Object.values(cameras).map((camera, index) => (
                    <div
                        key={index}
                        className="bg-mediumpurple p-3 rounded-lg flex flex-row gap-5 items-center"
                        onClick={() => setCameraConnectModal({ camera, show: true })}
                    >
                        <IconContext.Provider value={{ className: "text-foreground h-8 w-8" }}>
                            <BiSolidCctv />
                        </IconContext.Provider>
                        <div>
                            <p className="text-foreground font-bold">{camera.ip}</p>
                            <p className="text-lighterpurple font-semibold">{camera.mac}</p>
                        </div>
                    </div>
                ))}
                <div className="w-full flex justify-center items-center gap-3 mt-5">
                    <BeatLoader size={10} color="#867CA1" /> <p className="text-lighterpurple">Scanning Cameras</p>
                </div>
            </div>
        </div>
    );
};

export default DiscoveryPage;
