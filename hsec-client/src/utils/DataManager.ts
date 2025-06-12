// GetCameras, GetFrame, Etc.
// Include caching and GetCameras will take a bool whether to override the cache

import type { GenericResponse, GetCamerasResponse } from "../types";

export type DataEvent = "frame" | "camera_discovered" | "camera_pairing_success" | "camera_pairing_failure"
export type QueryType = "discover_cameras" | "stop_discovery" | "get_cameras" | "stream_camera" | "stop_stream" | "rename_camera" | "unpair_camera" | "pair_camera" | "login_pass" | "signup" | "login_session";

const SERVER_PORT = 34531

let websocketServer: WebSocket | null = null;

const base64ToIP = (b64: string) => {
    const binaryStr = atob(b64);
    if (binaryStr.length !== 4) alert("BAD CODE")
    const bytes = Array.from(binaryStr, char => char.charCodeAt(0));

    return bytes.join('.');
}

/*
{type: "discover_cameras", transaction_id: 12345}
{type: "stop_discovery", transaction_id: 12345}

*/

interface AwaitingResponse {
    transaction_id: number;
    resolve: (data: any) => void;
}



export class DataManager {
    private static awaitingResponses: AwaitingResponse[] = [];
    private static eventListeners: { [key: string]: (data: any) => void } = {};
    private static streamTransactionIds: { [key: string]: number } = {
        "discovering_cameras": -1,
        "streaming_frames": -1,
    };
    private static statusCallback: ((connected: boolean) => void) | null = null;

    static async onConnectionChange(callback: (connected: boolean) => void) {

        DataManager.statusCallback = callback;
    }

    static async connectToServer(serverCode: string, timeout: number): Promise<boolean> {
        return new Promise<boolean>((resolve, reject) => {
            const ip = base64ToIP(serverCode);
            websocketServer = new WebSocket(`ws://${ip}:${SERVER_PORT}`)
            let timer = setTimeout(() => {
                console.warn("Connection timed out, closing WebSocket");
                reject(new Error("Connection timed out"));
                websocketServer?.close()
                websocketServer = null;
            }, timeout)

            websocketServer.onopen = () => {
                clearTimeout(timer);
                resolve(true);

                console.log("Connected to server at", ip);

                if (!DataManager.statusCallback) return;
                console.log("WebSocket connection opened");
                DataManager.statusCallback(true);
            }

            websocketServer.onclose = () => {
                if (!DataManager.statusCallback) return;
                console.log("WebSocket connection closed");
                DataManager.statusCallback(false);
            }

            websocketServer.onerror = (error) => {
                if (!DataManager.statusCallback) return;
                console.error("WebSocket error:", error);
                DataManager.statusCallback(false);
            }

            websocketServer.onmessage = DataManager.message_handler
        })
    }

    private static message_handler(event: MessageEvent) {
        const response = JSON.parse(event.data);
        if (response.transaction_id) {
            if (DataManager.eventListeners[response.data?.type]) {
                // console.log("Event listener found for type:", response.data?.type);
                DataManager.eventListeners[response.data?.type](response.data);
            }
            const query = DataManager.awaitingResponses.find(r => r.transaction_id === response.transaction_id);
            if (query) {
                DataManager.awaitingResponses = DataManager.awaitingResponses.filter(r => r.transaction_id !== response.transaction_id);
                query.resolve(response);
            } else {
                console.warn("Received response for unknown transaction_id:", response.transaction_id);
            }
        }
    }

    static isConnected() {
        return websocketServer != null && websocketServer?.readyState != WebSocket.CLOSED && websocketServer?.readyState != WebSocket.CLOSING
    }

    private static sendRequest(type: QueryType, data: any, callback: (data: any) => void, tid?: number | null, timeout: number = 5000) {
        if (!DataManager.isConnected()) {
            console.error("Not connected to server");
            return -1;
        }

        const transaction_id = tid ? tid : Math.floor(Math.random() * 1000000);
        const request = JSON.stringify({
            type: type,
            transaction_id: transaction_id,
            ...data
        });
        websocketServer?.send(request);
        DataManager.awaitingResponses.push({
            transaction_id: transaction_id,
            resolve: (response: any) => callback(response)
        });

        setTimeout(() => {
            const index = DataManager.awaitingResponses.findIndex(r => r.transaction_id === transaction_id);
            if (index !== -1) {
                console.warn(`Request timed out for transaction_id: ${transaction_id}`);
                DataManager.awaitingResponses.splice(index, 1);
                callback({ error: "Request timed out" });
            }
        }, timeout);

        return transaction_id;
    }

    // stream
    static async startDiscoverCameras(): Promise<GenericResponse> {
        console.log("Starting camera discovery...");
        return new Promise((resolve, reject) => {
            if (!DataManager.isConnected()) {
                reject(new Error("Not connected to server"));
                return;
            }

            const transaction_id = DataManager.sendRequest("discover_cameras", {}, (data) => {
                if (data.error) resolve({ success: false, info: data.error });
                else resolve({ success: data.status === "success", info: data.data || "" });
            });

            DataManager.streamTransactionIds["discovering_cameras"] = transaction_id;
        })
    }

    static async stopDiscoverCameras(): Promise<GenericResponse> {
        console.log("Stopping camera discovery...");
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, info: "Not connected to server" });
                return;
            }

            const transaction_id = DataManager.streamTransactionIds["discovering_cameras"];
            if (transaction_id === -1) {
                resolve({ success: false, info: "No discovery in progress" });
                return;
            }

            DataManager.sendRequest("stop_discovery", {}, (data) => {
                if (data.error) resolve({ success: false, info: data.error });
                else resolve({ success: data.status === "success", info: data.data || "" });
            }, transaction_id);

            DataManager.streamTransactionIds["discovering_cameras"] = -1;
        })
    }

    static async getCameras(): Promise<GetCamerasResponse> {
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, cameras: [], info: "Not connected to server" });
                return;
            }

            DataManager.sendRequest("get_cameras", {}, (data) => {
                if (data.error) resolve({ success: false, cameras: [], info: data.error });
                else resolve({ success: data.status === "success", cameras: data.data || [], info: "" });
            })
        })
    }

    static async startStreamCamera(mac: string): Promise<GenericResponse> {
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, info: "Not connected to server" });
                return;
            }

            console.log("Starting camera stream for MAC:", mac);
            const transaction_id = DataManager.sendRequest("stream_camera", {mac}, (data) => {
                if (data.error) resolve({ success: false, info: data.error });
                else resolve({ success: data.status === "success", info: data.data || "" });
            });

            DataManager.streamTransactionIds["streaming_frames"] = transaction_id;
        })
    }

    static async stopStreamCamera(mac: string): Promise<GenericResponse> {
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, info: "Not connected to server" });
                return;
            }

            const transaction_id = DataManager.streamTransactionIds["streaming_frames"];
            if (transaction_id === -1) {
                resolve({ success: false, info: "No stream in progress" });
                return;
            }

            DataManager.sendRequest("stop_stream", {mac}, (data) => {
                if (data.error) resolve({ success: false, info: data.error });
                else resolve({ success: data.status === "success", info: data.data || "" });
            }, transaction_id);

            DataManager.streamTransactionIds["streaming_frames"] = -1;
        })
    }

    static async renameCamera(mac: string, new_name: string): Promise<GenericResponse> {
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, info: "Not connected to server" });
                return;
            }

            DataManager.sendRequest("rename_camera", { mac, new_name }, (data) => {
                if (data.error) resolve({ success: false, info: data.error });
                else resolve({ success: data.status === "success", info: data.data || "" });
            });
        })
    }

    static async removePairedCamera(mac: string): Promise<GenericResponse> {
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, info: "Not connected to server" });
                return;
            }

            DataManager.sendRequest("unpair_camera", { mac }, (data) => {
                if (data.error) resolve({ success: false, info: data.error });
                else resolve({ success: data.status === "success", info: data.data || "" });
            });
        })
    }

    static async pairCamera(ip: string, port: number, mac: string, code: string): Promise<GenericResponse> {
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, info: "Not connected to server" });
                return;
            }

            DataManager.sendRequest("pair_camera", { ip, code, port, mac }, (data) => {
                if (data.error) resolve({ success: false, info: data.error });
                else resolve({ success: data.status === "success", info: data.data || "" });
            });
        })
    }

    static addEventListener(event: DataEvent, callback: (data: any) => void) {
        DataManager.eventListeners[event] = callback;
    }

    static removeEventListener(event: DataEvent) {
        delete DataManager.eventListeners[event];
    }


    // -----
    static async passLogin(email: string, password: string): Promise<{ token: string; success: boolean; reason: string }> {
        return new Promise((resolve, reject) => {
            if (!DataManager.isConnected()) {
                reject(new Error("Not connected to server"));
                return;
            }

            DataManager.sendRequest("login_pass", { email, password }, (data) => {
                if (data.error) resolve({ token: "", success: false, reason: data.error });
                else resolve({ success: data.status === "success", token: data.data.session_id || "", reason: data.data.info || "" });
            })
        });
    }

    static async sessionLogin(email: string, token: string): Promise<{ success: boolean; reason: string }> {
        return new Promise((resolve, reject) => {
            if (!DataManager.isConnected()) {
                reject(new Error("Not connected to server"));
                return;
            }

            DataManager.sendRequest("login_session", { email, session_id: token }, (data) => {
                if (data.error) resolve({ success: false, reason: data.error });
                else resolve({ success: data.status === "success", reason: data.data.info || "" });
            })
        });
    }

    static async createAccount(email: string, password: string): Promise<{ token: string; success: boolean; reason?: string }> {
        return new Promise((resolve, reject) => {
            if (!DataManager.isConnected()) {
                reject(new Error("Not connected to server"));
                return;
            }

            DataManager.sendRequest("signup", { email, password }, (data) => {
                if (data.error) resolve({ token: "", success: false, reason: data.error });
                else resolve({ success: data.status === "success", token: data.data.session_id || "", reason: data.data.info || "" });
            })
        });
    }
}