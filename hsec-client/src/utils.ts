export const macToId = (mac: string) => {
    const macParts = mac.split(":").slice(3, 6);
    const macId = macParts.join("");
    return macId;
}