import React from "react";
import type { Camera } from "../types";
import { TbDeviceCctvFilled } from "react-icons/tb";
import { MdEdit } from "react-icons/md";
import { IconContext } from "react-icons/lib";

interface Props {
    camera: Camera;
}

const CameraCard = ({ camera }: Props) => {
    return (
        <div className="w-full bg-primary2 rounded-xl overflow-hidden flex flex-col min-h-[200px]">
            <div className="flex flex-row justify-between p-3 items-center">
                <IconContext.Provider value={{ className: "text-secondary click-effect" }}>
                    <div className="flex flex-row gap-3 items-center">
                        <TbDeviceCctvFilled size={20} />
                        <p className="text-secondary font-bold tracking-wider">{camera.name}</p>
                    </div>
                    <MdEdit size={20} />
                </IconContext.Provider>
            </div>
            <img src={"data:image/png;base64," + camera.last_frame} alt="" className="w-full h-50 " />
        </div>
    );
};

export default CameraCard;
