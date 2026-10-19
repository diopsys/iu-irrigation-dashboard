/* Lader für das Panel der Integration „IU Irrigation Dashboard“.
 * HA liefert /local/ mit 31 Tagen Browser-Cache aus. Der eigentliche Code
 * (irrigation-app.js) wird deshalb mit Zeitstempel geladen und ist nach
 * jeder Änderung sofort aktiv – ohne ?v= und ohne HA-Neustart.
 * Top-level await: HA legt das Element erst an, wenn es definiert ist.
 */
await import(`./irrigation-app.js?t=${Date.now()}`);
