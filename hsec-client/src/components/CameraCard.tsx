import React from "react";
import type { Camera } from "../types";
import { TbDeviceCctvFilled } from "react-icons/tb";
import { MdEdit } from "react-icons/md";
import { IconContext } from "react-icons/lib";
import Modal from "./Modal";
import Input from "./Input";
import Button from "./Button";
import { DataManager } from "../utils/DataManager";
import { VscDebugDisconnect } from "react-icons/vsc";
import { AiOutlineDisconnect } from "react-icons/ai";

interface Props {
    camera: Camera;
    updateCameraList: () => void;
    onClick?: () => void;
}

const CameraCard = ({ camera, onClick, updateCameraList }: Props) => {
    const [showRenameModal, setShowRenameModal] = React.useState(false);
    const [showUnpairModal, setShowUnpairModal] = React.useState(false);
    const [currCameraName, setCurrCameraCode] = React.useState(camera.name);
    const [loadingUnpair, setLoadingUnpair] = React.useState(false);

    const renameCamera = async (name: string) => {
        // Simulate renaming camera
        DataManager.renameCamera(camera.mac, name).then((res) => {
            if (res.success) {
                setShowRenameModal(false);
                updateCameraList()
            } else {
                alert("Failed to rename camera: " + res.info);
            }
        }).catch((err) => {
            console.error("Error renaming camera:", err);
            alert("An error occurred while renaming the camera.");
        })
    };

    return (
        <div className="w-full bg-lightpurple rounded-xl overflow-hidden flex flex-col min-h-[200px]">
            <Modal
                visible={showRenameModal}
                onClose={() => {
                    setShowRenameModal(false);
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
            <Modal
                visible={showUnpairModal}
                onClose={() => {
                    setShowRenameModal(false);
                }}
            >
                <p className="text-foreground text-sm">Unpair Camera, Are you sure?</p>
                <p className="text-lighterpurple text-xs mb-6">This action will remove the camera from the database and unlink it completely, the only way to recover it would be re-pairing it.</p>
                
                <Button
                    text="Unpair Camera"
                    className="mt-8 w-full"
                    isLoading={loadingUnpair}
                    onClick={() => {
                        setLoadingUnpair(true);
                        DataManager.unpairCamera(camera.mac).then((res) => {
                            if (res.success) {
                                setShowUnpairModal(false);
                                updateCameraList();
                                setLoadingUnpair(false);
                            } else {
                                alert("Failed to unpair camera: " + res.info);
                                setLoadingUnpair(false);
                            }
                        }).catch((err) => {
                            console.error("Error unpairing camera:", err);
                            alert("An error occurred while unpairing the camera.");
                            setLoadingUnpair(false);
                        });
                    }}
                />

                {/* <Button
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
                /> */}
            </Modal>

            <div className="flex flex-row justify-between items-center px-4 py-2">
                <IconContext.Provider value={{ className: "text-purple" }}>
                    <div className="flex flex-row gap-3 items-center">
                        <TbDeviceCctvFilled size={20} />
                        <p className="text-purple font-bold tracking-wider">{camera.name}</p>
                    </div>
                    <div className="flex flex-row gap-3 justify-end">
                        <button onClick={() => setShowUnpairModal(true)} className="p-2">
                            <AiOutlineDisconnect size={20} />
                        </button>
                        <button onClick={() => setShowRenameModal(true)} className="p-2">
                            <MdEdit size={20} />
                        </button>
                    </div>
                </IconContext.Provider>
            </div>
            <div className="relative">
                {!camera.connected &&
                    <div className="absolute top-0 left-0 w-full h-full bg-black bg-opacity-60 flex items-center justify-center text-foreground text-8xl">
                        <VscDebugDisconnect />
                    </div>}
                <img src={"data:image/png;base64," + camera.last_frame} alt="" className="w-full h-40 " onClick={onClick} />
            </div>
        </div>
    );
};

export default CameraCard;
