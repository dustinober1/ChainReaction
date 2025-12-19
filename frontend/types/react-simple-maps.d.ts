declare module 'react-simple-maps' {
    import { ComponentType, ReactNode, CSSProperties } from 'react';

    export interface ComposableMapProps {
        projection?: string;
        projectionConfig?: {
            scale?: number;
            center?: [number, number];
            rotate?: [number, number, number];
        };
        width?: number;
        height?: number;
        style?: CSSProperties;
        children?: ReactNode;
    }

    export interface ZoomableGroupProps {
        center?: [number, number];
        zoom?: number;
        minZoom?: number;
        maxZoom?: number;
        translateExtent?: [[number, number], [number, number]];
        children?: ReactNode;
        onMoveStart?: (event: any) => void;
        onMove?: (event: any) => void;
        onMoveEnd?: (event: any) => void;
    }

    export interface GeographiesProps {
        geography: string | object;
        children: (data: { geographies: Geography[] }) => ReactNode;
    }

    export interface Geography {
        rsmKey: string;
        properties: Record<string, any>;
        geometry: any;
    }

    export interface GeographyProps {
        geography: Geography;
        fill?: string;
        stroke?: string;
        strokeWidth?: number;
        style?: {
            default?: CSSProperties & { outline?: string };
            hover?: CSSProperties & { outline?: string };
            pressed?: CSSProperties & { outline?: string };
        };
        onMouseEnter?: (event: any) => void;
        onMouseLeave?: (event: any) => void;
        onClick?: (event: any) => void;
    }

    export interface MarkerProps {
        coordinates: [number, number];
        children?: ReactNode;
        style?: CSSProperties;
        onClick?: (event: any) => void;
        onMouseEnter?: (event: any) => void;
        onMouseLeave?: (event: any) => void;
    }

    export interface LineProps {
        from: [number, number];
        to: [number, number];
        stroke?: string;
        strokeWidth?: number;
        strokeOpacity?: number;
        strokeLinecap?: 'butt' | 'round' | 'square';
        strokeDasharray?: string;
    }

    export const ComposableMap: ComponentType<ComposableMapProps>;
    export const ZoomableGroup: ComponentType<ZoomableGroupProps>;
    export const Geographies: ComponentType<GeographiesProps>;
    export const Geography: ComponentType<GeographyProps>;
    export const Marker: ComponentType<MarkerProps>;
    export const Line: ComponentType<LineProps>;
}
