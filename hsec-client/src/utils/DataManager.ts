// GetCameras, GetFrame, Etc.
// Include caching and GetCameras will take a bool whether to override the cache

export type DataEvent = "FRAME" | "CAMERA_DISCOVERED" | "CAMERA_PAIRING_SUCCESS" | "CAMERA_PAIRING_FAILURE"

export class DataManager {

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