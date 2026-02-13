import QtQuick

Rectangle {
    id: root
    width: 400
    height: 300
    color: "white"

    property string greeting: "Hello, QML!"
    property int counter: 0

    function increment() {
        counter += 1
    }

    Text {
        id: label
        anchors.centerIn: parent
        text: root.greeting
    }

    MouseArea {
        anchors.fill: parent
        onClicked: {
            root.increment()
            label.text = root.greeting + " " + root.counter
        }
    }

    Helper {
        id: helper
        value: root.counter
    }
}
