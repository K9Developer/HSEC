export interface Camera {
    name: string;
    last_frame: string;
    ip: string;
    mac: string;
    connected?: boolean;
    red_zone?: [number, number][];
}

export interface User {
    email: string;
    logged_in: boolean;
    session_token: string | null;
}

export interface LoginResponse {
    success: boolean;
    message: string;
    user: User | null;
}

export interface HsecNotification {
    type: string;
    title: string;
    message: string;
    mac: string;
    timestamp: number;
    frame?: string; // Optional, as not all notifications may have a frame
}

// ---------

export interface GenericResponse {
    success: boolean;
    info: string;
}

export interface GetCamerasResponse extends GenericResponse {
    cameras: Camera[];
}

export interface GetNotificationsResponse extends GenericResponse {
    notifications: HsecNotification[];
}