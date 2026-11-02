
"use strict";

// =====================================
// NOTIFICACIONES PUSH - PARROQUIAAPP
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    const capacitor = window.Capacitor;

    // =====================================
    // COMPROBAR PLATAFORMA
    // =====================================

    if (!capacitor || !capacitor.isNativePlatform()) {
        console.log("Notificaciones: entorno web detectado.");
        return;
    }

    if (capacitor.getPlatform() !== "android") {
        console.log("Notificaciones: plataforma no compatible.");
        return;
    }

    console.log("Notificaciones: Capacitor Android detectado.");

    // =====================================
    // COMPLEMENTOS NATIVOS
    // =====================================

    const PushNotifications = capacitor.Plugins?.PushNotifications;
    const FirebaseAppCheck = capacitor.Plugins?.FirebaseAppCheck;

    if (!PushNotifications) {
        console.error(
            "Notificaciones: complemento PushNotifications no disponible."
        );
        return;
    }

    console.log(
        "Notificaciones: complemento PushNotifications disponible."
    );

    // =====================================
    // SOLICITAR PERMISOS
    // =====================================

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

    // =====================================
    // SOLICITAR REGISTRO FCM
    // =====================================

    async function registrarDispositivo() {

        try {

            await PushNotifications.register();

            console.log(
                "Notificaciones: registro solicitado a Firebase."
            );

        } catch (error) {

            console.error(
                "Notificaciones: error al solicitar registro FCM.",
                error
            );

        }
    }

    // =====================================
    // REGISTRAR TOKEN EN EL BACKEND
    // =====================================

    PushNotifications.addListener(
        "registration",
        async function (token) {

            try {

                // Comprobar token FCM
                if (!token.value) {
                    throw new Error("Token FCM vacío.");
                }

                // Comprobar disponibilidad de App Check
                if (!FirebaseAppCheck) {
                    throw new Error(
                        "Firebase App Check no disponible."
                    );
                }

                // Obtener token App Check
                const resultadoAppCheck =
                    await FirebaseAppCheck.getToken({
                        forceRefresh: false
                    });

                if (!resultadoAppCheck.token) {
                    throw new Error(
                        "No se pudo obtener el token App Check."
                    );
                }

                // Enviar registro al backend
                const respuesta = await fetch(
                    "/notificaciones/registrar",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-Firebase-AppCheck": resultadoAppCheck.token
                        },
                        body: JSON.stringify({
                            token: token.value,
                            plataforma: "android"
                        })
                    }
                );

                if (!respuesta.ok) {
                    throw new Error(
                        "Error HTTP " + respuesta.status
                    );
                }

                console.log(
                    "Notificaciones: dispositivo registrado correctamente."
                );

            } catch (error) {

                console.error(
                    "Notificaciones: error al registrar el dispositivo.",
                    error
                );

            }
        }
    );

    // =====================================
    // ERRORES DE REGISTRO FCM
    // =====================================

    PushNotifications.addListener(
        "registrationError",
        function (error) {

            console.error(
                "Notificaciones: error durante el registro en Firebase.",
                error
            );

        }
    );

    // =====================================
    // INICIAR PROCESO
    // =====================================

    solicitarPermisoNotificaciones();

});
