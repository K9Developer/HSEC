// GetCameras, GetFrame, Etc.
// Include caching and GetCameras will take a bool whether to override the cache

import type { GenericResponse, GetCamerasResponse, GetNotificationsResponse, PlaybackChunkResponse } from "../types";
import showPopup from "./PopupManager";

export type DataEvent = "frame" | "camera_discovered" | "red_zone_trigger"
export type QueryType = "discover_cameras" | "stop_discovery" | "get_cameras" | "stream_camera" | "stop_stream" | "rename_camera" | "unpair_camera" | "pair_camera" | "login_pass" | "signup" | "login_session" | "request_password_reset" | "reset_password" | "share_camera" | "save_polygon" | "get_notifications" | "send_fcm_token" | "update_alert_categories" | "get_playback_chunk" | "get_playback_range";

const SERVER_PORT = 34531

let websocketServer: WebSocket | null = null;

const base64ToIP = (b64: string) => {
    const binaryStr = atob(b64);
    if (binaryStr.length !== 4) showPopup("Invalid server code length, must be 4 bytes", "error");
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
        if (response.transaction_id !== undefined) {
            if (DataManager.eventListeners[response.data?.type]) {
                response.data.success = response.status === "success";
                DataManager.eventListeners[response.data?.type](response.data);
            }
            const query = DataManager.awaitingResponses.find(r => r.transaction_id === response.transaction_id);
            if (query) {
                DataManager.awaitingResponses = DataManager.awaitingResponses.filter(r => r.transaction_id !== response.transaction_id);
                query.resolve(response);
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

    static async updateAlertCategories(mac: string, categories: string[]): Promise<GenericResponse> {
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, info: "Not connected to server" });
                return;
            }

            DataManager.sendRequest("update_alert_categories", { mac, categories }, (data) => {
                if (data.error) resolve({ success: false, info: data.error });
                else resolve({ success: data.status === "success", info: data.data || "" });
            });
        })
    }

    static async getPlaybackChunk(mac: string, start: Date, end: Date): Promise<PlaybackChunkResponse> {
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, info: "Not connected to server", camera_id: mac, time_started: start, video_data: "", duration: 0, size: [0, 0] });
                return;
            }

            DataManager.sendRequest("get_playback_chunk", { mac, start_date: start.toISOString(), end_date: end.toISOString() }, (data) => {
                if (data.error) resolve({ success: false, info: data.error, camera_id: mac, time_started: start, video_data: "", duration: 0, size: [0, 0] });
                else resolve({
                    success: data.status === "success",
                    camera_id: mac,
                    time_started: new Date(data.data.time_started),
                    video_data: data.data.video_data || "",
                    duration: data.data.duration || 0,
                    size: data.data.size || [0, 0],
                    info: data.data.info || ""
                });
            });
        })
    }

    static async getPlaybackRange(mac: string): Promise<{ success: boolean; info: string; start_date: Date; end_date: Date }> {
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, info: "Not connected to server", start_date: new Date(0), end_date: new Date(0) });
                return;
            }

            DataManager.sendRequest("get_playback_range", { mac }, (data) => {
                if (data.error) resolve({ success: false, info: data.error, start_date: new Date(0), end_date: new Date(0) });
                else resolve({
                    success: data.status === "success",
                    info: data.data.info || "",
                    start_date: new Date(data.data.start_date),
                    end_date: new Date(data.data.end_date)
                });
            });
        })
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
                resolve({ success: false, cameras: [], categories: [], info: "Not connected to server" });
                return;
            }

            DataManager.sendRequest("get_cameras", {}, (data) => {
                if (data.error) resolve({ success: false, cameras: [], categories: [], info: data.error });
                else resolve({ success: data.status === "success", cameras: data.data.cameras || [], categories: data.data.categories, info: "" });
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
            const transaction_id = DataManager.sendRequest("stream_camera", { mac }, (data) => {
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

            DataManager.sendRequest("stop_stream", { mac }, (data) => {
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

    static async unpairCamera(mac: string): Promise<GenericResponse> {
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

    static async shareCamera(mac: string, email: string): Promise<GenericResponse> {
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, info: "Not connected to server" });
                return;
            }

            DataManager.sendRequest("share_camera", { mac, email }, (data) => {
                if (data.error) resolve({ success: false, info: data.error });
                else resolve({ success: data.status === "success", info: data.data || "" });
            });
        })
    }

    static async saveRedzone(mac: string, polygon: [number, number][]): Promise<GenericResponse> {
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, info: "Not connected to server" });
                return;
            }

            DataManager.sendRequest("save_polygon", { mac, polygon }, (data) => {
                if (data.error) resolve({ success: false, info: data.error });
                else resolve({ success: data.status === "success", info: data.data || "" });
            });
        })
    }

    static async getNotifications(): Promise<GetNotificationsResponse> {
        return new Promise((resolve, _) => {
            if (!DataManager.isConnected()) {
                resolve({ success: false, info: "Not connected to server", notifications: [] });
                return;
            }

            DataManager.sendRequest("get_notifications", {}, (data) => {
                if (data.error) resolve({ success: false, info: data.error, notifications: [] });
                else resolve({ success: data.status === "success", notifications: data.data || [], info: "" });
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

    static async requestPasswordReset(email: string): Promise<{ success: boolean; reason: string, timeLeft?: number }> {
        return new Promise((resolve, reject) => {
            if (!DataManager.isConnected()) {
                reject(new Error("Not connected to server"));
                return;
            }

            DataManager.sendRequest("request_password_reset", { email }, (data) => {
                if (data.error) resolve({ success: false, reason: data.error });
                else resolve({ success: data.status === "success", reason: data.data.info || "", timeLeft: data.data.time_left || 0 });
            })
        });
    }

    static async resetPassword(email: string, reset_code: string, new_password: string): Promise<{ success: boolean; reason: string }> {
        return new Promise((resolve, reject) => {
            if (!DataManager.isConnected()) {
                reject(new Error("Not connected to server"));
                return;
            }

            DataManager.sendRequest("reset_password", { email, reset_code, new_password }, (data) => {
                if (data.error) resolve({ success: false, reason: data.error });
                else resolve({ success: data.status === "success", reason: data.data.info || "" });
            })
        });
    }

    static async sendFCMToken(token: string): Promise<{ success: boolean; info: string }> {
        return new Promise((resolve, reject) => {
            if (!DataManager.isConnected()) {
                reject(new Error("Not connected to server"));
                return;
            }

            DataManager.sendRequest("send_fcm_token", { token }, (data) => {
                if (data.error) resolve({ success: false, info: data.data });
                else resolve({ success: data.status === "success", info: data.data });
            })
        });
    }
}