/** 네이버 지도 API v3 전역 타입 */
declare global {
  interface Window {
    naver?: typeof naver;
    navermap_authFailure?: () => void;
  }
}

declare namespace naver.maps {
  class LatLng {
    constructor(lat: number, lng: number);
    lat(): number;
    lng(): number;
  }
  class LatLngBounds {
    constructor(sw?: LatLng, ne?: LatLng);
    extend(latLng: LatLng): LatLngBounds;
  }
  interface MapOptions {
    center?: LatLng;
    zoom?: number;
    scaleControl?: boolean;
    logoControl?: boolean;
    mapDataControl?: boolean;
    zoomControl?: boolean;
  }
  class Map {
    constructor(container: string | HTMLElement, options?: MapOptions);
    setCenter(center: LatLng): void;
    setZoom(level: number): void;
    getCenter(): LatLng;
    getZoom(): number;
    fitBounds(bounds: LatLngBounds, padding?: number): void;
  }
  interface MarkerOptions {
    position: LatLng;
    map: Map;
    icon?: string | object;
    title?: string;
  }
  class Marker {
    constructor(options: MarkerOptions);
    setMap(map: Map | null): void;
  }
  class InfoWindow {
    constructor(options?: { content?: string; position?: LatLng; borderWidth?: number });
    setContent(content: string): void;
    open(map: Map, anchor?: Marker | LatLng): void;
    close(): void;
    getMap(): Map | null;
  }
  namespace Event {
    function addListener(target: object, eventName: string, handler: () => void): MapEventListener;
  }
  interface MapEventListener {
    remove(): void;
  }
}

export {};
