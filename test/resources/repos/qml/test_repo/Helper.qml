import QtQuick

Item {
    id: root

    property int value: 0
    property string description: "Helper component"

    function doubleValue() {
        return value * 2
    }

    function formatValue() {
        return description + ": " + value
    }
}
