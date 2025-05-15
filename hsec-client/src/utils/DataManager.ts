// GetCameras, GetFrame, Etc.
// Include caching and GetCameras will take a bool whether to override the cache

export type DataEvent = "FRAME" | "CAMERA_DISCOVERED" | "CAMERA_PAIRING_SUCCESS" | "CAMERA_PAIRING_FAILURE"
const SERVER_PORT = 34531

let websocketServer: WebSocket | null = null;

const base64ToIP = (b64: string) => {
    const binaryStr = atob(b64);
    if (binaryStr.length !== 4) alert("BAD CODE")
    const bytes = Array.from(binaryStr, char => char.charCodeAt(0));

    return bytes.join('.');
}

export class DataManager {


    static async connectToServer(serverCode: string, timeout: number): Promise<boolean> {
        return new Promise<boolean>((resolve, _) => {
            const ip = base64ToIP(serverCode);
            websocketServer = new WebSocket(`wss://${ip}:${SERVER_PORT}`)
            let timer = setTimeout(()=>{
                resolve(false);
                websocketServer?.close()
                websocketServer = null;
            }, timeout)

            websocketServer.onopen = () => {
                clearTimeout(timer);
                resolve(true);
            }
        })
    }

    static isConnected() {
        return websocketServer != null && websocketServer?.readyState != WebSocket.CLOSED && websocketServer?.readyState != WebSocket.CLOSING
    }

    static async requestSessionToken(email: string, password: string): Promise<{ token: string; id: string }> {
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                // Simulate a successful login
                resolve({ token: "abc123", id: "123" });
            }, 1000);
        });
    }

    static async createAccount(email: string, password: string): Promise<{ token: string; id: string; success: boolean; reason?: string }> {
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                // Simulate a successful account creation
                resolve({ token: "abc123", id: "123", success: true });
            }, 1000);
        });
    }

    static addEventListener(event: DataEvent, callback: (data: any) => void) {
        // Simulate adding an event listener
        console.log(`Event listener added for ${event}`);
    }

    static removeEventListener(event: DataEvent, callback: (data: any) => void) {
        // Simulate removing an event listener
        console.log(`Event listener removed for ${event}`);
    }

    static connectToCamera(ip: string, code: string) {
        // Simulate connecting to a camera
        console.log(`Connecting to camera at ${ip} with code ${code}`);
    }

    static renameCamera(cameraId: string, name: string) {
        // Simulate renaming a camera
        console.log(`Renaming camera ${cameraId} to ${name}`);

    }
}