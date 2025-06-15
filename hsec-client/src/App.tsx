import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage.tsx";
import AccountPage from "./pages/AccountPage.tsx";
import CameraViewer from "./pages/CameraViewer.tsx";
import DiscoveryPage from "./pages/DiscoveryPage.tsx";
import ConnectToServerPage from "./pages/ConnectToServerPage.tsx";
import UserContext from "./contexts/UserContext.tsx";
import type { User } from "./types.tsx";
import { UserManager } from "./utils/AccountManager.ts";
import { DataManager } from "./utils/DataManager.ts";
import Button from "./components/Button.tsx";
import Input from "./components/Input.tsx";
import Modal from "./components/Modal.tsx";
import ForgotPasswordPage from "./pages/ForgotPasswordPage.tsx";
import NotificationPage from "./pages/NotificationPage.tsx";

const requestNotificationPermission = async () => {
    if ("Notification" in window && Notification.permission !== "granted") {
        try {
            const permission = await Notification.requestPermission();
            if (permission === "granted") {
                console.log("Notification permission granted");
            } else {
                console.warn("Notification permission denied");
            }
        } catch (error) {
            console.error("Failed to request notification permission:", error);
        }
    }
}

const App = () => {
    const [user, setUser] = useState<null | User>(null);
    const [showServerCode, setShowServerCode] = useState(false);
    const [currServerCode, setCurrServerCode] = useState("");
    const [connectingToServer, setConnectingToServer] = useState(false);
    const [connected, setConnected] = useState(false);

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
                    alert(reason);
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
            alert("Red zone triggered! Please check the camera feed for more details.");
        });
    }, []);

    useEffect(() => {
        const localUser = UserManager.getLocalUser();
        if (localUser && !user) {
            handleAutoLogin();
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
            alert("Failed to connect to server. Please check the server code and try again.");
            setConnectingToServer(false);
            localStorage.removeItem("server_code");
            setCurrServerCode("");
            return false;
        }
    }

    useEffect(() => {
        const func = async () => {
            console.log("Checking connection status: ", connected);
            const code = localStorage.getItem("server_code");
            if (code) {
                const succ = await connect(code);
                if (!succ) {
                    setShowServerCode(true);
                    console.log(1111111111111111, window.location.href)
                    if (window.location.pathname !== "/") window.location.href = "/";
                }
            }

            if (connected && !user) {
                setShowServerCode(false);
                handleAutoLogin();
            } else {
                setShowServerCode(true);
                if (window.location.pathname !== "/") window.location.href = "/";
            }
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
                <Input
                    placeholder="Server Code"
                    onChange={(val: string) => {
                        setCurrServerCode(val);
                        return true;
                    }}
                    pattern={/.+/}
                    startingValue={""}
                />
                <Button
                    text="Connect"
                    className="mt-8 w-full"
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
                            }).catch((err) => {
                                console.error("Failed to connect to server:", err);
                                alert("Failed to connect to server. Please check the server code and try again.");
                                setConnectingToServer(false);
                                localStorage.removeItem("server_code");
                            })
                    }}
                />
            </Modal>

            <UserContext.Provider value={{ user, setUser }}>
                <BrowserRouter>
                    <Routes>
                        <Route index element={<HomePage />} />
                        <Route path="connect" element={<ConnectToServerPage />} />
                        <Route path="account" element={<AccountPage />} />
                        <Route path="notifications" element={<NotificationPage />} />
                        <Route path="discover" element={<DiscoveryPage />} />
                        <Route path="account/forgot-pass" element={<ForgotPasswordPage />} />
                        <Route path="camera/:cameraId" element={<CameraViewer />} />
                        <Route path="*" element={<div>404 Not Found</div>} />
                    </Routes>
                </BrowserRouter>
            </UserContext.Provider>
        </>
    );
};

export default App;
