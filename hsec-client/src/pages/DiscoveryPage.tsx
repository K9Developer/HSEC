import React, { useEffect } from "react";
import { IconContext } from "react-icons";
import { IoMdArrowRoundBack } from "react-icons/io";
import { BeatLoader } from "react-spinners";
import { DataManager } from "../utils/DataManager";
import { BiSolidCctv } from "react-icons/bi";
import Modal from "../components/Modal";
import Input from "../components/Input";
import Button from "../components/Button";

interface CameraDiscoveredType {
    ip: string;
    mac: string;
}

const TMP_CAMERA_DATA = [
    { ip: "10.10.10.1", mac: "00:00:00:00:00:01" },
    { ip: "10.10.10.2", mac: "00:00:00:00:00:02" },
    { ip: "10.10.10.3", mac: "00:00:00:00:00:03" },
];

interface CameraConnectModal {
    camera: CameraDiscoveredType | null;
    show: boolean;
}

const DiscoveryPage = () => {
    const [currCameraCode, setCurrCameraCode] = React.useState("");
    const [cameras, setCameras] = React.useState<CameraDiscoveredType[]>([]);
    const [cameraConnectModal, setCameraConnectModal] = React.useState<CameraConnectModal>({
        camera: null,
        show: false,
    });
    const [expectingCameraPair, setExpectingCameraPair] = React.useState(false);

    const cameraPairTimeout = () => {
        setExpectingCameraPair(false);
        setCameraConnectModal({ camera: null, show: false });
        alert("Camera Pairing Timed Out");
    };

    const onCameraPairSuccess = (data: any) => {
        console.log("Camera Pair Success", data);
        setExpectingCameraPair(false);
        history.pushState(null, "", "/");
        setCameraConnectModal({ camera: null, show: false });
        // Handle camera pairing success
    };

    const onCameraPairFailure = (data: any) => {
        console.log("Camera Pair Failure", data);
        alert("Camera Pairing Failed");
        setExpectingCameraPair(false);
        setCameraConnectModal({ camera: null, show: false });
        // Handle camera pairing failure
    };

    const onCameraDiscovered = ({ ip, mac }: CameraDiscoveredType) => {
        console.log("Camera Discovered", ip, mac);
        if (cameras.find((camera) => camera.mac === mac)) return;
        setCameras((prev) => [...prev, { ip, mac }]);
    };

    const attemptCameraConnect = (camera: CameraDiscoveredType | null, code: string) => {
        if (!camera) return;
        setExpectingCameraPair(true);
        DataManager.connectToCamera(camera.ip, code);
    };

    useEffect(() => {
        setTimeout(() => {
            setCameras(TMP_CAMERA_DATA);
        }, 1000);
        DataManager.addEventListener("CAMERA_DISCOVERED", onCameraDiscovered);
        DataManager.addEventListener("CAMERA_PAIRING_SUCCESS", onCameraPairSuccess);
        DataManager.addEventListener("CAMERA_PAIRING_FAILURE", onCameraPairFailure);
        return () => {
            DataManager.removeEventListener("CAMERA_DISCOVERED", onCameraDiscovered);
            DataManager.removeEventListener("CAMERA_PAIRING_SUCCESS", onCameraPairSuccess);
            DataManager.removeEventListener("CAMERA_PAIRING_FAILURE", onCameraPairFailure);
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
                        setTimeout(cameraPairTimeout, 4000);
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
                {cameras.map((camera, index) => (
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
