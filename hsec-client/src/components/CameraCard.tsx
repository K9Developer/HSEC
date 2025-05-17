import React from "react";
import type { Camera } from "../types";
import { TbDeviceCctvFilled } from "react-icons/tb";
import { MdEdit } from "react-icons/md";
import { IconContext } from "react-icons/lib";
import Modal from "./Modal";
import Input from "./Input";
import Button from "./Button";
import { DataManager } from "../utils/DataManager";

interface Props {
    camera: Camera;
    onClick?: () => void;
}

const CameraCard = ({ camera, onClick }: Props) => {
    const [showModal, setShowModal] = React.useState(false);
    const [currCameraName, setCurrCameraCode] = React.useState(camera.name);

    const renameCamera = (name: string) => {
        // Simulate renaming camera
        DataManager.renameCamera(camera.mac, name);
        setShowModal(false);
    };

    return (
        <div className="w-full bg-lightpurple rounded-xl overflow-hidden flex flex-col min-h-[200px]">
            <Modal
                visible={showModal}
                onClose={() => {
                    setShowModal(false);
                }}
            >
                <p className="text-foreground text-sm">Rename Camera</p>
                <p className="text-lighterpurple text-xs mb-6">Attempting to rename camera {camera.name}</p>
                <Input
                    placeholder="Camera Name"
                    onChange={(val: string) => {
                        setCurrCameraCode(val);
                        return true;
                    }}
                    pattern={/.+/}
                    startingValue={camera.name}
                />
                <Button
                    text="Rename"
                    className="mt-8 w-full"
                    disabled={currCameraName === camera.name || currCameraName === ""}
                    onClick={() => {
                        if (currCameraName === camera.name) return;
                        if (currCameraName === "") {
                            alert("Camera name cannot be empty");
                            return;
                        }
                        renameCamera(currCameraName);
                    }}
                />
            </Modal>

            <div className="flex flex-row justify-between items-center">
                <IconContext.Provider value={{ className: "text-purple" }}>
                    <div className="flex flex-row gap-3 items-center p-3">
                        <TbDeviceCctvFilled size={20} />
                        <p className="text-purple font-bold tracking-wider">{camera.name}</p>
                    </div>
                    <button onClick={() => setShowModal(true)} className="p-3">
                        <MdEdit size={20} />
                    </button>
                </IconContext.Provider>
            </div>
            <img src={"data:image/png;base64," + camera.last_frame} alt="" className="w-full h-40 " onClick={onClick} />
        </div>
    );
};

export default CameraCard;
