LIGHT_THEME = r"""
/*====================================================
    GLOBAL
====================================================*/

QWidget {
    background-color: #F1F1F1;
    color: #0E0E0E;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QMainWindow {
    background-color: #F1F1F1;
}

/*====================================================
    SIDEBAR
====================================================*/

#sidebar {
    background-color: #FFFFFF;
    border-right: 2px solid #D7D7D7;
}

#brandLabel {
    background: transparent;
    color: #012645;
    font-size: 22px;
    font-weight: 700;
}

#productLabel {
    background: transparent;
    color: #012645;
    font-size: 13px;
}

#sidebarFooter {
    background: transparent;
    color: #888888;
    font-size: 10px;
}

/*====================================================
    NAVIGATION
====================================================*/

#navigationList {
    background: transparent;
    border: none;
    outline: none;
}

#navigationList::item {
    background: transparent;
    color: #012645;
    padding: 12px 18px;
    border: none;
    border-left: 4px solid transparent;
    margin: 2px 0px;
}

#navigationList::item:hover {
    background-color: #EAFBFD;
    border-left: 4px solid #03BFD8;
}

#navigationList::item:selected {
    background-color: #D7F8FC;
    border-left: 4px solid #03BFD8;
    color: #012645;
    font-weight: 700;
}

#navigationPanel {
    background-color: #FFFFFF;
    border-right: 2px solid #D7D7D7;
}

#navigationTitle {
    background: transparent;
    color: #012645;
    font-size: 16px;
    font-weight: 700;
}

#navigationSubtitle {
    background: transparent;
    color: #012645;
    font-size: 12px;
}

#navigationButton {
    background-color: transparent;
    color: #012645;
    border: none;
    border-left: 4px solid transparent;
    border-radius: 0px;
    padding: 10px 12px;
    text-align: left;
}

#navigationButton:hover {
    background-color: #EAFBFD;
    border-left-color: #03BFD8;
}

#navigationButton:checked {
    background-color: #D7F8FC;
    border-left-color: #03BFD8;
    font-weight: 700;
}

#navigationFooter {
    background: transparent;
    color: #888888;
    font-size: 10px;
}

/*====================================================
    HEADER
====================================================*/

#topHeader {
    background-color: white;
    border: 1px solid #DADADA;
    border-radius: 0px;
}

#pageTitle {
    background: transparent;
    color: #012645;
    font-size: 22px;
    font-weight: 700;
}

#connectionPlaceholder {
    background: transparent;
    color: #03BFD8;
    font-weight: 700;
}

/*====================================================
    PAGE TITLES
====================================================*/

#sectionHeading {

    background: transparent;

    color: #012645;

    font-size: 28px;

    font-weight: 700;
}

#sectionSubtitle {

    background: transparent;

    color: #666666;

    font-size: 12px;
}

/*====================================================
    DASHBOARD CARDS
====================================================*/

#dashboardCard {

    background-color: white;

    border: 1px solid #D8D8D8;

    border-radius: 0px;
}

#dashboardCard:hover {

    border-color: #03BFD8;
}

#cardTitle {

    background: transparent;

    color: #012645;

    font-size: 12px;

    font-weight: 600;
}

#numericValue {

    background: transparent;

    color: #012645;

    font-size: 30px;

    font-weight: 700;
}

#numericUnit {

    background: transparent;

    color: #666666;

    font-size: 12px;
}

#statusText {

    background: transparent;

    color: #012645;

    font-size: 16px;

    font-weight: 600;
}

#faultName {

    background: transparent;

    color: #012645;

    font-size: 14px;

    font-weight: 700;
}

#faultDetail {

    background: transparent;

    color: #666666;

    font-size: 11px;
}

#graphUnit {

    background: transparent;

    color: #666666;
}

/*====================================================
    FAULT BADGES
====================================================*/

QLabel[activeFault="false"] {

    background-color: #EAFBFD;

    color: #012645;

    border: 1px solid #03BFD8;

    border-radius: 0px;

    padding: 4px 10px;

    font-weight: 700;
}

QLabel[activeFault="true"] {

    background-color: #FDE5F0;

    color: #F92785;

    border: 1px solid #F92785;

    border-radius: 0px;

    padding: 4px 10px;

    font-weight: 700;
}

/*====================================================
    SCROLLBAR
====================================================*/

QScrollBar:vertical {

    background: #EFEFEF;

    width: 10px;
}

QScrollBar::handle:vertical {

    background: #03BFD8;

    min-height: 30px;
}

QScrollBar::handle:vertical:hover {

    background: #012645;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {

    height: 0px;
}

QScrollBar:horizontal {

    background: #EFEFEF;

    height: 10px;
}

QScrollBar::handle:horizontal {

    background: #03BFD8;

    min-width: 30px;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {

    width: 0px;
}

/*====================================================
    TELEMETRY RECEIVER
====================================================*/

#receiverCard {
    background-color: #FFFFFF;
    border: 1px solid #D8D8D8;
    border-radius: 0px;
}

#receiverCard:hover {
    border-color: #03BFD8;
}

#receiverCardTitle {
    background: transparent;
    color: #012645;
    font-size: 12px;
    font-weight: 700;
}

#receiverStateText {
    background: transparent;
    color: #012645;
    font-size: 12px;
    font-weight: 700;
}

#receiverDetailHeading {
    background: transparent;
    color: #666666;
    font-size: 10px;
}

#receiverDetailValue {
    background: transparent;
    color: #012645;
    font-size: 11px;
    font-weight: 600;
}

#receiverMessage {
    background: transparent;
    color: #666666;
    font-size: 10px;
}

#receiverDeviceCombo {
    background-color: #FFFFFF;
    color: #012645;
    border: 1px solid #D8D8D8;
    border-radius: 0px;
    padding: 5px 8px;
    min-height: 25px;
}

#receiverDeviceCombo:hover {
    border-color: #03BFD8;
}

#receiverDeviceCombo:focus {
    border-color: #03BFD8;
}

#receiverDeviceCombo:disabled {
    background-color: #F1F1F1;
    color: #888888;
}

#receiverDeviceCombo::drop-down {
    background-color: #EAFBFD;
    border: none;
    border-left: 1px solid #D8D8D8;
    width: 24px;
}

#receiverDeviceCombo QAbstractItemView {
    background-color: #FFFFFF;
    color: #012645;
    border: 1px solid #D8D8D8;
    outline: none;
    selection-background-color: #D7F8FC;
    selection-color: #012645;
}

#receiverRefreshButton,
#receiverActionButton {
    background-color: #FFFFFF;
    color: #012645;
    border: 1px solid #D8D8D8;
    border-radius: 0px;
    padding: 4px 8px;
    font-weight: 600;
    min-height: 25px;
}

#receiverRefreshButton:hover,
#receiverActionButton:hover {
    background-color: #EAFBFD;
    border-color: #03BFD8;
}

#receiverRefreshButton:pressed,
#receiverActionButton:pressed {
    background-color: #D7F8FC;
}

#receiverActionButton:disabled {
    background-color: #F1F1F1;
    color: #888888;
    border-color: #D8D8D8;
}

#receiverStatusIndicator {
    background-color: #888888;
    border: 1px solid #666666;
    border-radius: 5px;
}

#receiverStatusIndicator[connectionState="connected"] {
    background-color: #03BFD8;
    border-color: #012645;
}

#receiverStatusIndicator[connectionState="scanning"],
#receiverStatusIndicator[connectionState="connecting"],
#receiverStatusIndicator[connectionState="reconnecting"] {
    background-color: #F4C542;
    border-color: #B58B00;
}

#receiverStatusIndicator[connectionState="disconnected"] {
    background-color: #888888;
    border-color: #666666;
}

#receiverStatusIndicator[connectionState="error"] {
    background-color: #F92785;
    border-color: #B5175E;
}

/*====================================================
    DASHBOARD STATUS INDICATORS
====================================================*/

#dashboardStatusIndicator {
    background-color: #A8ADB2;
    border: 1px solid #747A80;
    border-radius: 5px;
}

#dashboardStatusIndicator[statusState="connected"] {
    background-color: #03BFD8;
    border-color: #012645;
}

#dashboardStatusIndicator[statusState="waiting"] {
    background-color: #F4C542;
    border-color: #B58B00;
}

#dashboardStatusIndicator[statusState="error"] {
    background-color: #F92785;
    border-color: #B5175E;
}

#dashboardStatusIndicator[statusState="unknown"] {
    background-color: #A8ADB2;
    border-color: #747A80;
}

#graphPlaceholder {
    background-color: #FFFFFF;
    border-top: 1px solid #E4E4E4;
}

"""
# Additional selectors used by the Stage 1-5 cache-backed dashboard pages.
LIGHT_THEME += r"""
#graphLegendText {
    background: transparent;
    color: #012645;
    font-size: 10px;
}
"""
