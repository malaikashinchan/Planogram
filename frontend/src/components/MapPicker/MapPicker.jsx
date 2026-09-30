import React, { useEffect } from 'react';
import {
    MapContainer,
    TileLayer,
    Marker,
    useMapEvents,
    useMap,
} from 'react-leaflet';

import L from 'leaflet';

import 'leaflet/dist/leaflet.css';
import './MapPicker.css';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';


delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
    iconRetinaUrl: markerIcon2x,
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
});


const DEFAULT_CENTER = [20.5937, 78.9629];


const MapClickHandler = ({ onLocationSelect }) => {
    useMapEvents({
        click(event) {
            onLocationSelect(
                event.latlng.lat,
                event.latlng.lng
            );
        },
    });

    return null;
};

const MapUpdater = ({ center, zoom }) => {
    const map = useMap();
    useEffect(() => {
        map.setView(center, zoom);
    }, [center, zoom, map]);
    return null;
};

const MapPicker = ({
    latitude,
    longitude,
    onLocationSelect,
    mapCenter,
    mapZoom,
}) => {

    const hasLocation =
        latitude !== null &&
        latitude !== undefined &&
        longitude !== null &&
        longitude !== undefined;

    const center = hasLocation
        ? [latitude, longitude]
        : mapCenter || DEFAULT_CENTER;
        
    const zoom = hasLocation ? 16 : mapZoom || 5;


    return (
        <div className="map-picker">

            <MapContainer
                center={center}
                zoom={zoom}
                scrollWheelZoom={true}
                className="map-container"
            >

                <TileLayer
                    attribution='&copy; OpenStreetMap contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                <MapUpdater center={center} zoom={zoom} />

                <MapClickHandler
                    onLocationSelect={onLocationSelect}
                />

                {hasLocation && (
                    <Marker
                        position={[latitude, longitude]}
                    />
                )}

            </MapContainer>

        </div>
    );
};

export default MapPicker;