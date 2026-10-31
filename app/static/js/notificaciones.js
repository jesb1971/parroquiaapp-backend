
"use strict";

// =====================================
// NOTIFICACIONES PUSH - PARROQUIAAPP
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    const capacitor = window.Capacitor;

    if (!capacitor || !capacitor.isNativePlatform()) {
        console.log("Notificaciones: entorno web detectado.");
        return;
    }

    if (capacitor.getPlatform() !== "android") {
        console.log("Notificaciones: plataforma no compatible.");
        return;
    }

    console.log("Notificaciones: Capacitor Android detectado.");
	
	const PushNotifications = capacitor.Plugins?.PushNotifications;

	if (!PushNotifications) {
		console.error("Notificaciones: complemento nativo no disponible.");
		return;
	}

	console.log("Notificaciones: complemento PushNotifications disponible.");
	
	async function solicitarPermisoNotificaciones() {
    try {
        let permisos = await PushNotifications.checkPermissions();

        if (permisos.receive === "prompt") {
            permisos = await PushNotifications.requestPermissions();
        }

        if (permisos.receive === "granted") {
			console.log("Notificaciones: permiso concedido.");
			await registrarDispositivo();
		} else {
			console.log("Notificaciones: permiso no concedido.");
		}

    } catch (error) {
        console.error(
            "Notificaciones: error al comprobar permisos.",
            error
        );
    }
}

	async function registrarDispositivo() {
    try {
        await PushNotifications.register();
        console.log("Notificaciones: registro solicitado a Firebase.");
    } catch (error) {
        console.error(
            "Notificaciones: error al registrar el dispositivo.",
            error
        );
    }
}
	PushNotifications.addListener("registration", function (token) {
		console.log("Notificaciones: token FCM recibido.");
		// Posteriormente enviaremos el token al backend de forma segura.
	});
	
	PushNotifications.addListener("registrationError", function (error) {
    console.error(
        "Notificaciones: error durante el registro en Firebase.",
        error
    );
});

	solicitarPermisoNotificaciones();

});
