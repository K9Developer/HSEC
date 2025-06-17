import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage.tsx";
import AccountPage from "./pages/AccountPage.tsx";
import CameraViewer from "./pages/CameraViewer.tsx";
import DiscoveryPage from "./pages/DiscoveryPage.tsx";
import UserContext from "./contexts/UserContext.tsx";
import type { User } from "./types.tsx";
import { UserManager } from "./utils/AccountManager.ts";
import { DataManager } from "./utils/DataManager.ts";
import Button from "./components/Button.tsx";
import Input from "./components/Input.tsx";
import Modal from "./components/Modal.tsx";
import ForgotPasswordPage from "./pages/ForgotPasswordPage.tsx";
import NotificationPage from "./pages/NotificationPage.tsx";
import { getFCMToken } from "./utils.ts";
import { ToastContainer } from 'react-toastify';
import showPopup from "./utils/Popupmanager.ts";
import { CgQr } from "react-icons/cg";
import { IconContext } from "react-icons";
import { MdKeyboardAlt } from "react-icons/md";
import AnimatedQRScanner from "./components/AnimatedQRScanner.tsx";
import { Scanner } from '@yudiel/react-qr-scanner'; // gotta have this import for the qr to work even tho thats not used directly (FOR SOME FUCKIN REASON)

const App = () => {
    const [user, setUser] = useState<null | User>(null);
    const [showServerCode, setShowServerCode] = useState(false);
    const [currServerCode, setCurrServerCode] = useState("");
    const [connectingToServer, setConnectingToServer] = useState(false);
    const [connected, setConnected] = useState(false);
    const [qrMode, setQrMode] = useState(false);

    const handleFCMToken = async () => {
        console.log("Requesting notification permission...");
        const fcmToken = await getFCMToken();
        if (fcmToken) {
            try {
                const response = await DataManager.sendFCMToken(fcmToken);
                if (!response.success) console.error("Failed to send FCM token:", response.info);
                else console.log("FCM token sent successfully");
            } catch (error) {
                console.error("Error sending FCM token:", error);
            }
        } else {
            console.warn("FCM token is null, notifications may not work properly.");
        }
        return fcmToken;
    }

    const handleAutoLogin = async () => {
        console.log("Checking for local user...");
        console.log(user, DataManager.isConnected());

        if (!user && DataManager.isConnected()) {
            const localUser = UserManager.getLocalUser();
            console.log("Local user found:", localUser);
            if (!localUser) return;
            if (localUser.session_token && localUser.email && !localUser.logged_in) {
                const { success, reason } = await DataManager.sessionLogin(localUser.email, localUser.session_token);
                if (!success) {
                    showPopup(reason, "error");
                    UserManager.logoutUser();
                    console.error("Failed to log in with session token:", reason);
                } else {
                    setUser({
                        ...localUser,
                        logged_in: true,
                    });
                    console.log("Logged in with session token successfully");
                }
            }
        }
    }

    useEffect(() => {
        DataManager.onConnectionChange((connected) => {
            console.log("Connection status changed:", connected);
            setConnected(connected);
        })

        DataManager.addEventListener("red_zone_trigger", () => {
            showPopup("Red zone triggered!", "warning", {
                onClick: () => {
                    if (window.location.pathname !== "/notifications") window.location.href = "/notifications";
                    else window.location.reload();
                }
            });
        });

    }, []);

    useEffect(() => {
        const localUser = UserManager.getLocalUser();
        if (localUser && !user) {
            handleAutoLogin();
        }

        if (user?.logged_in) {
            handleFCMToken()
        }
    }, [user]);

    const connect = async (serverCode: string) => {
        console.log("Connecting to server with code:", serverCode);
        setCurrServerCode(serverCode);
        setConnectingToServer(true);
        try {
            await DataManager.connectToServer(serverCode, 5000);
            setShowServerCode(false);
            setCurrServerCode("");
            setConnectingToServer(false);
            localStorage.setItem("server_code", serverCode);
            return true;
        } catch (err) {
            console.error("Failed to connect to server:", err);
            showPopup("Failed to connect to server. Please check the server code and try again.", "error");
            setConnectingToServer(false);
            localStorage.removeItem("server_code");
            setCurrServerCode("");
            return false;
        }
    }

    useEffect(() => {
        const func = async () => {
            const code = localStorage.getItem("server_code");
            if (code) {
                const succ = await connect(code);
                if (!succ) setShowServerCode(true);
            }

            if (connected && !user) {
                setShowServerCode(false);
                handleAutoLogin();
            } else setShowServerCode(true);
        }

        func();

    }, [connected]);

    return (
        <>
            <Modal
                visible={showServerCode}
                onClose={() => { }}
                showCloseButton={false}
            >
                <p className="text-foreground text-sm">Connect to server</p>
                {
                    qrMode ?
                        <div className="w-50 h-50 rounded-2xl overflow-hidden mt-2">
                            <AnimatedQRScanner onResult={(result) => {
                                console.log("QR Code Result:", result);
                                if (result.length < 6) {
                                    showPopup("Invalid server code scanned. Please try again.", "error");
                                    return;
                                }
                                setCurrServerCode(result);
                                return true;
                            }} freezeOnScan/>
                        </div>
                        : <Input
                            placeholder="Server Code"
                            onChange={(val: string) => {
                                setCurrServerCode(val);
                                return true;
                            }}
                            pattern={/.+/}
                            startingValue={""}
                        />
                }
                <div className="flex flex-row gap-3 mt-8 items-center">
                    <Button
                        text="Connect"
                        className="w-full h-10"
                        isLoading={connectingToServer}
                        disabled={currServerCode.length < 6}
                        onClick={() => {
                            setConnectingToServer(true);
                            DataManager.connectToServer(currServerCode, 5000)
                                .then(async () => {
                                    setShowServerCode(false);
                                    setCurrServerCode("");
                                    setConnectingToServer(false);
                                    localStorage.setItem("server_code", currServerCode);
                                    if (window.location.pathname !== "/") window.location.href = "/";
                                }).catch((err) => {
                                    console.error("Failed to connect to server:", err);
                                    showPopup("Failed to connect to server. Please check the server code and try again.", "error");
                                    setConnectingToServer(false);
                                    localStorage.removeItem("server_code");
                                })
                        }}
                    />
                    <IconContext.Provider value={{ className: "text-foreground h-full w-10" }}>
                        {
                            qrMode ?
                                <MdKeyboardAlt onClick={() => setQrMode(false)} />
                                :
                                <CgQr onClick={() => setQrMode(true)} />

                        }
                    </IconContext.Provider>
                </div>
            </Modal>

            <UserContext.Provider value={{ user, setUser }}>
                <BrowserRouter>
                    <Routes>
                        <Route index element={<HomePage />} />
                        <Route path="account" element={<AccountPage />} />
                        <Route path="notifications" element={<NotificationPage />} />
                        <Route path="discover" element={<DiscoveryPage />} />
                        <Route path="account/forgot-pass" element={<ForgotPasswordPage />} />
                        <Route path="camera/:cameraId" element={<CameraViewer />} />
                        <Route path="*" element={<div>404 Not Found</div>} />
                    </Routes>
                </BrowserRouter>
            </UserContext.Provider>

            <ToastContainer />
        </>
    );
};

export default App;
