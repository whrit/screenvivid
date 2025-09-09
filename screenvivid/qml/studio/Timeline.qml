import QtQuick 6.7
import QtQuick.Controls 6.7
import QtQuick.Controls.Material 6.7
import QtQuick.Layouts 6.7

Item {
    id: timeline
    width: studioWindow.fps * studioWindow.videoLen * studioWindow.pixelsPerFrame
    height: 60

    function formatTime(frame) {
        var fps = studioWindow.fps
        var totalSeconds = frame / fps
        var minutes = Math.floor(totalSeconds / 60)
        var seconds = Math.floor(totalSeconds % 60)
        return minutes.toString().padStart(2, '0') + ':' + seconds.toString().padStart(2, '0')
    }

    Repeater {
        model: Math.ceil(studioWindow.videoLen) + 1

        delegate: Item {
            width: studioWindow.fps * studioWindow.pixelsPerFrame
            height: 60
            x: studioWindow.fps * studioWindow.pixelsPerFrame * index

            readonly property int timeLabelWidth: 20

            Item {
                width: parent.timeLabelWidth
                height: parent.height

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Item { Layout.fillHeight: true; Layout.fillWidth: true }

                    Label {
                        Layout.alignment: Qt.AlignCenter
                        text: qsTr("" + index)
                    }

                    Item {
                        Layout.alignment: Qt.AlignCenter

                        Rectangle {
                            width: 4
                            height: 4
                            radius: 2
                            color: "white"
                            anchors.centerIn: parent
                        }
                    }

                    Item { Layout.fillHeight: true; Layout.fillWidth: true }
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    var xPos = Math.max(0,
                                        studioWindow.fps * studioWindow.pixelsPerFrame * index + mouseX
                                        - parent.timeLabelWidth / 2)
                    var currentFrame = Math.round(xPos / studioWindow.pixelsPerFrame)
                    videoController.jump_to_frame(currentFrame)
                }
            }
        }
    }

    Repeater {
        model: videoController.clickEvents

        delegate: Rectangle {
            visible: modelData[4] === "press"
            width: 4
            height: 12
            radius: 2
            color: videoController.currentFrame === modelData[2] ? studioWindow.accentColor : "white"
            x: modelData[2] * studioWindow.pixelsPerFrame - width / 2
            anchors.bottom: parent.bottom

            ToolTip {
                visible: area.containsMouse
                text: formatTime(modelData[2])
            }

            MouseArea {
                id: area
                anchors.fill: parent
                hoverEnabled: true
                onClicked: videoController.jump_to_frame(modelData[2])
            }
        }
    }
}

