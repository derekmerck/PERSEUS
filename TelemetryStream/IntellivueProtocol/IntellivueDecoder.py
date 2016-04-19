"""
@author: uagrawal last update: 1/22/16
"""

from __future__ import unicode_literals

from io import open
import struct
import codecs
import copy
import logging
import os

# For path'd reads of label data
package_directory = os.path.dirname(os.path.abspath(__file__))

class IntellivueDecoder(object):
    """
    This class contains all of the data structures defined in the Data Interface
    Programming Guide, methods to read in the various messages, and methods to
    write messages to communicate with a Philips Intellivue Monitor.

    It encodes messages in Intellivue format and serializes them, and decodes
    serial messages into Intellivue format.

    Decoded messages may be distilled to relevant telemetry data using the sister
    class, IntellivueDistiller.
    """
    def __init__(self):
        """
        There are four main data structures (all dictionaries):

            DataTypes -

                This dictionary stores all of the data structures defined
                in the Programming Guide in a tree like format.
                As a key it has the name of the data type, and the values are
                either keys to another entry, an int (8, 16, 32), or alternative
                data type (ie VariableLabel, AttributeList, VariableData)

                The methods in this class can iterate through DataTypes until
                one of the basic types is reached and either store the values
                into a dictionary or output them into a binary message.

                Notes:
                    If DataTypes[0] = 8, DataTypes[1] = n, where n is the number
                    of uint8s that needs to be read in succession

                    If DataTypes[0] = AttributeList, should have
                    DataTypes[1] = [list of attributes] (not necessary for
                    messages where AttributeList just read in, not written)

                    length_, ASNLength_, LILength_, all have the name of the
                    data structure that is the endpoint of their length appended
                    to the name (and are stored at the index where they belong)

            DataKeys -

                This dictionary converts all of the binary values to the
                label indicated in the programming guide, or vice versa

                Notes:
                    Need to comment out all of the alternative options
                    because can only write one at a time to output_messages

            MessageLists -

                Dictionary that defines the order of all the messages to send
                and recieve from the Intellivue

            MessageParameters -

                Stores the default values of the message parameters, but can
                be overriden if input is provided
        """
        self.DataTypes = {}
        self.DataKeys = {}
        self.MessageLists = {}
        self.MessageParameters = {}

        self.DataTypes['Nomenclature'] = [32]
        self.DataTypes['ROapdus'] = ['ro_type', 'length_final']
        self.DataTypes['ro_type'] = [16]
        self.DataTypes['length'] = [16]
        self.DataTypes['ROIVapdu'] = ['invoke_id', 'CMDType', 'length_final']
        self.DataTypes['invoke_id'] = [16]
        self.DataTypes['CMDType'] = [16]
        self.DataTypes['EventReportArgument'] = ['ManagedObjectID', 'RelativeTime', 'OIDType', 'length']
        self.DataTypes['ManagedObjectID'] = ['OIDType', 'GlbHandle']
        self.DataTypes['OIDType'] = [16]
        self.DataTypes['GlbHandle'] = ['MdsContext', 'Handle']
        self.DataTypes['ConnectIndInfo'] = ['AttributeList']
        self.DataTypes['RelativeTime'] = [32]
        self.DataTypes['MdsContext'] = [16]
        self.DataTypes['Handle'] = [16]
        self.DataTypes['count'] = [16]
        self.DataTypes['Type'] = ['NomPartition', 'OIDType']
        self.DataTypes['NomPartition'] = [16]
        self.DataTypes['SystemLocal'] = ['text_catalog_revision', 'Language', 'StringFormat']
        self.DataTypes['text_catalog_revision'] = [32]
        self.DataTypes['Language'] = [16]
        self.DataTypes['StringFormat'] = [16]
        self.DataTypes['IPAddressInfo'] = ['MACAddress', 'IPAddress', 'Subnet_Mask']
        self.DataTypes['MACAddress'] = [8, 6]
        self.DataTypes['IPAddress'] = [8, 4]
        self.DataTypes['Subnet_Mask'] = [8, 4]
        self.DataTypes['ProtoSupport'] = ['count', 'length', 'ProtoSupportEntry']
        self.DataTypes['ProtoSupportEntry'] = ['ApplProtoID', 'TransProtoID', 'port_number', 'ProtoOptions']
        self.DataTypes['ApplProtoID'] = [16]
        self.DataTypes['TransProtoID'] = [16]
        self.DataTypes['port_number'] = [16]
        self.DataTypes['ProtoOptions'] = [16]
        self.DataTypes['SystemModel'] = ['manufacturer', 'model_number']
        self.DataTypes['manufacturer'] = ['VariableLabel']
        self.DataTypes['model_number'] = ['VariableLabel']
        self.DataTypes['ProductionSpec'] = ['count', 'length', 'ProdSpecEntry']
        self.DataTypes['ProdSpecEntry'] = ['spec_type', 'component_id', 'prod_spec']
        self.DataTypes['spec_type'] = [16]
        self.DataTypes['component_id'] = [16]
        self.DataTypes['prod_spec'] = ['VariableLabel']
        self.DataTypes['AssocReqSessionHeader'] = ['AssocReqSessionHead', 'LILength_AssocReqPresentationTrailer']
        self.DataTypes['AssocReqPresentationHeader'] = ['AssocReqPresentationHead1', 'LILength_AssocReqPresentationTrailer', 'AssocReqPresentationHead2']
        self.DataTypes['AssocReqUserData'] = ['ASNLength_MDSEUserInfoStd', 'MDSEUserInfoStd']
        self.DataTypes['MDSEUserInfoStd'] = ['ProtocolVersion', 'NomenclatureVersion', 'FunctionalUnits', 'SystemType', 'StartupMode', 'option_list', 'supported_aprofiles']
        self.DataTypes['ProtocolVersion'] = [32]
        self.DataTypes['NomenclatureVersion'] = [32]
        self.DataTypes['FunctionalUnits'] = [32]
        self.DataTypes['SystemType'] = [32]
        self.DataTypes['StartupMode'] = [32]
        self.DataTypes['option_list'] = ['AttributeList', ['Null']]
        self.DataTypes['supported_aprofiles'] = ['AttributeList', ['NOM_POLL_PROFILE_SUPPORT']]
        self.DataTypes['NullAttribute'] = [32]
        self.DataTypes['PollProfileSupport'] = ['PollProfileRevision', 'min_poll_period', 'max_mtu_rx', 'max_mtu_tx', 'max_bw_tx', 'PollProfileOptions', 'PollProfileSupport_optional_packages']
        self.DataTypes['PollProfileRevision'] = [32]
        self.DataTypes['min_poll_period'] = ['RelativeTime']
        self.DataTypes['max_mtu_rx'] = [32]
        self.DataTypes['max_mtu_tx'] = [32]
        self.DataTypes['max_bw_tx'] = [32]
        self.DataTypes['PollProfileOptions'] = [32]
        self.DataTypes['PollProfileSupport_optional_packages'] = ['AttributeList', ['NOM_ATTR_POLL_PROFILE_EXT']]
        self.DataTypes['PollProfileExt'] = ['PollProfileExtOptions', 'ext_attr']
        self.DataTypes['PollProfileExtOptions'] = [32]
        self.DataTypes['ext_attr'] = ['AttributeList', ['Null']]
        self.DataTypes['AssocRespUserData'] = ['ASNLength_MDSEUserInfoStd', 'MDSEUserInfoStd']
        self.DataTypes['MDSCreateInfo'] = ['ManagedObjectID', 'MDSAttributeList']
        self.DataTypes['MDSAttributeList'] = ['AttributeList']
        self.DataTypes['SPpdu'] = ['session_id', 'p_context_id']
        self.DataTypes['session_id'] = [16]
        self.DataTypes['p_context_id'] = [16]
        self.DataTypes['AssociationInvokeID'] = [16]
        self.DataTypes['OperatingMode'] = [16]
        self.DataTypes['ApplicationArea'] = [16]
        self.DataTypes['LineFrequency'] = [16]
        self.DataTypes['Safety'] = [16]
        self.DataTypes['Altitude'] = [-16]
        self.DataTypes['MdsGenSystemInfo'] = ['count', 'length_MdsGenSystemInfo', 'MdsGenSystemInfoEntry']
        self.DataTypes['MdsGenSystemInfoEntry'] = ['choice', 'length_MdsGenSystemInfoEntry', 'SystemPulseInfo']
        self.DataTypes['choice'] = [16]
        self.DataTypes['SystemPulseInfo'] = ['system_pulse', 'alarm_source']
        self.DataTypes['system_pulse'] = ['ManagedObjectID']
        self.DataTypes['alarm_source'] = ['ManagedObjectID']
        self.DataTypes['MDSStatus'] = [16]
        self.DataTypes['String'] = ['length_String', 'value']
        self.DataTypes['AbsoluteTime'] = ['century', 'year', 'month', 'day', 'hour', 'minute', 'second', 'sec_fractions']
        self.DataTypes['century'] = [8, 'bcd']
        self.DataTypes['year'] = [8, 'bcd']
        self.DataTypes['month'] = [8, 'bcd']
        self.DataTypes['day'] = [8, 'bcd']
        self.DataTypes['hour'] = [8, 'bcd']
        self.DataTypes['minute'] = [8, 'bcd']
        self.DataTypes['second'] = [8, 'bcd']
        self.DataTypes['sec_fractions'] = [8, 'bcd']
        self.DataTypes['SystemSpec'] = ['count', 'length_SystemSpec', 'SystemSpecEntry']
        self.DataTypes['SystemSpecEntry'] = ['OIDType', 'length_SystemSpecEntry', 'SystemSpecEntryValue']
        self.DataTypes['SystemSpecEntryValue'] = ['count', 'length_SystemSpecEntryValue', 'MdibObjectSupportEntry']
        self.DataTypes['MdibObjectSupportEntry'] = ['Type', 'max_inst']
        self.DataTypes['max_inst'] = [32]
        self.DataTypes['EventReportResult'] = ['ManagedObjectID', 'RelativeTime', 'OIDType', 'length_final']
        self.DataTypes['ActionArgument'] = ['ManagedObjectID', 'scope', 'action_type', 'length_final']
        self.DataTypes['scope'] = [32]
        self.DataTypes['action_type'] = [16]
        self.DataTypes['PollMdibDataReq'] = ['poll_number', 'Type', 'OIDType']
        self.DataTypes['poll_number'] = [16]
        self.DataTypes['RORSapdu'] = ['invoke_id', 'CMDType', 'length_final']
        self.DataTypes['ActionResult'] = ['ManagedObjectID', 'OIDType', 'length_final']
        self.DataTypes['PollMdibDataReply'] = ['poll_number', 'RelativeTime', 'AbsoluteTime', 'Type', 'OIDType', 'PollInfoList']
        self.DataTypes['PollInfoList'] = ['count', 'length_PollInfoList', 'SingleContextPoll']
        self.DataTypes['SingleContextPoll'] = ['MdsContext', 'poll_info']
        self.DataTypes['poll_info'] = ['count', 'length_poll_info', 'ObservationPoll']
        self.DataTypes['ObservationPoll'] = ['Handle', 'AttributeList']
        self.DataTypes['ROLRSapdu'] = ['RolrsId', 'invoke_id', 'CMDType', 'length_final']
        self.DataTypes['RolrsId'] = ['state', 'Rolrs_count']
        self.DataTypes['state'] = [8, 1]
        self.DataTypes['Rolrs_count'] = [8, 1]
        self.DataTypes['MetricSpec'] = ['update_period', 'MetricCategory', 'MetricAccess', 'MetricStructure', 'MetricRelevance']
        self.DataTypes['update_period'] = ['RelativeTime']
        self.DataTypes['MetricCategory'] = [16]
        self.DataTypes['MetricAccess'] = [16]
        self.DataTypes['MetricStructure'] = ['ms_struct', 'ms_comp_no']
        self.DataTypes['ms_struct'] = [8, 1]
        self.DataTypes['ms_comp_no'] = [8, 1]
        self.DataTypes['MetricRelevance'] = [16]
        self.DataTypes['DispResolution'] = ['pre_point', 'post_point']
        self.DataTypes['pre_point'] = [8,1]
        self.DataTypes['post_point'] = [8,1]
        self.DataTypes['SimpleColour'] = [16]
        self.DataTypes['PrivateAttribute'] = [16]
        self.DataTypes['NuObsValue'] = ['SCADAType', 'MeasurementState', 'UNITType', 'FLOATType']
        self.DataTypes['SCADAType'] = [16]
        self.DataTypes['MeasurementState'] = [16]
        self.DataTypes['UNITType'] = [16]
        self.DataTypes['NuObsValCmp'] = ['count', 'length_NuObsValCmp', 'NuObsValue']
        self.DataTypes['PollMdibDataReqExt'] = ['poll_number', 'Type', 'OIDType', 'poll_ext_attr']
        self.DataTypes['PollDataReqPeriod'] = ['RelativeTime']
        self.DataTypes['poll_ext_attr'] = ['AttributeList', ['NOM_ATTR_TIME_PD_POLL']]
        self.DataTypes['ReleaseRequested'] = ['ReleaseReq']
        self.DataTypes['AssocAbortMsg'] = ['AssocAbort']
        self.DataTypes['PollMdibDataReplyExt'] = ['poll_number', 'sequence_no', 'RelativeTime', 'AbsoluteTime', 'Type', 'OIDType', 'PollInfoList']
        self.DataTypes['sequence_no'] = [16]
        self.DataTypes['GetArgument'] = ['ManagedObjectID', 'scope', 'ArgumentAttributeIdList']
        self.DataTypes['ArgumentAttributeIdList'] = ['AttributeIdList', ['NOM_ATTR_POLL_RTSA_PRIO_LIST', 'NOM_ATTR_POLL_NU_PRIO_LIST']]
        self.DataTypes['GetResult'] = ['ManagedObjectID', 'AttributeList']
        self.DataTypes['TextIdLabel'] = ['count', 'length_TextIdLabel', 'TextId']
        self.DataTypes['TextId'] = [32]
        self.DataTypes['SetArgument'] = ['ManagedObjectID', 'scope', 'ModificationList']
        self.DataTypes['ModificationList'] = ['count', 'length_ModificationList', 'AttributeModEntry']
        self.DataTypes['AttributeModEntry'] = ['ModifyOperator', 'PriorityList']
        self.DataTypes['PriorityList'] = ['OIDType','length_PriorityList','TextIdLabel']
        self.DataTypes['ModifyOperator'] = [16]
        self.DataTypes['SetResult'] = ['ManagedObjectID', 'AttributeList']
        self.DataTypes['SaObsValueCmp'] = ['count', 'length_SaObsValueCmp', 'SaObsValue']
        self.DataTypes['SaObsValue'] = ['SCADAType', 'MeasurementState', 'PhysioValue']
        self.DataTypes['PhysioValue'] = ['VariableData']
        self.DataTypes['SaSpec'] = ['array_size', 'SampleType', 'SaFlags']
        self.DataTypes['array_size'] = [16]
        self.DataTypes['SampleType'] = ['sample_size', 'significant_bits']
        self.DataTypes['sample_size'] = [8, 1]
        self.DataTypes['significant_bits'] = [8, 1]
        self.DataTypes['SaFlags'] = [16]
        self.DataTypes['MetricState'] = [16]
        self.DataTypes['ScaleRangeSpec16'] = ['lower_absolute_value', 'upper_absolute_value', 'lower_scaled_value', 'upper_scaled_value']
        self.DataTypes['lower_absolute_value'] = ['FLOATType']
        self.DataTypes['upper_absolute_value'] = ['FLOATType']
        self.DataTypes['lower_scaled_value'] = [16]
        self.DataTypes['upper_scaled_value'] = [16]
        self.DataTypes['SaVisualGrid16'] = ['count', 'length_SaVisualGrid16', 'SaGridEntry16']
        self.DataTypes['SaGridEntry16'] = ['absolute_value', 'scaled_value', 'level']
        self.DataTypes['absolute_value'] = ['FLOATType']
        self.DataTypes['scaled_value'] = [16]
        self.DataTypes['level'] = [16]
        self.DataTypes['SaFixedValSpec16'] = ['count', 'length_SaFixedValSpec16', 'SaFixedValSpecEntry16']
        self.DataTypes['SaFixedValSpecEntry16'] = ['SaFixedValId', 'sa_fixed_val']
        self.DataTypes['SaFixedValId'] = [16]
        self.DataTypes['sa_fixed_val'] = [16]
        self.DataTypes['MeasureMode'] = [16]
        self.DataTypes['SaCalData16'] = ['lower_absolute_value', 'upper_absolute_value', 'lower_scaled_value', 'upper_scaled_value', 'increment', 'cal_type']
        self.DataTypes['increment'] = [16]
        self.DataTypes['cal_type'] = [16]
        self.DataTypes['ScaledRange16'] = ['lower_scaled_value', 'upper_scaled_value']
        self.DataTypes['DeviceAlertCondition'] = ['device_alert_state', 'al_stat_chg_cnt', 'max_p_alarm', 'max_t_alarm', 'max_aud_alarm']
        self.DataTypes['device_alert_state'] = ['AlertState']
        self.DataTypes['AlertState'] = [16]
        self.DataTypes['al_stat_chg_cnt'] = [16]
        self.DataTypes['max_p_alarm'] = ['AlertType']
        self.DataTypes['max_t_alarm'] = ['AlertType']
        self.DataTypes['max_aud_alarm'] = ['AlertType']
        self.DataTypes['AlertType'] = [16]
        self.DataTypes['DevAlarmList'] = ['count','length_DevAlarmList', 'DevAlarmEntry']
        self.DataTypes['DevAlarmEntry'] = ['al_source_code', 'AlertType', 'AlertState', 'ManagedObjectID', 'StrAlMonInfo']
        self.DataTypes['StrAlMonInfo'] = ['al_inst_no','TextId','AlertPriority','AlertFlags','String']
        self.DataTypes['al_inst_no'] = [16]
        self.DataTypes['AlertPriority'] = [16]
        self.DataTypes['AlertFlags'] = [16]

        self.DataKeys['AlertFlags'] = {
            'BEDSIDE_AUDIBLE': b'\x40\x00',
            'CENTRAL_AUDIBLE': b'\x20\x00',
            'VISUAL_LATCHING': b'\x10\x00',
            'AUDIBLE_LATCHING': b'\x08\x00',
            'SHORT_YELLOW_EXTENSION': b'\x04\x00',
            'DERIVED': b'\x02\x00',
            b'\x40\x00': 'BEDSIDE_AUDIBLE',
            b'\x20\x00': 'CENTRAL_AUDIBLE',
            b'\x10\x00': 'VISUAL_LATCHING',
            b'\x08\x00': 'AUDIBLE_LATCHING',
            b'\x04\x00': 'SHORT_YELLOW_EXTENSION',
            b'\x02\x00': 'DERIVED'
        }

        self.DataKeys['AlertState'] = {
            'AL_INHIBITED': b'\x80\x00',
            'AL_SUSPENDED': b'\x40\x00',
            'AL_LATCHED': b'\x20\x00',
            'AL_SILENCED_RESET': b'\x10\x00',
            'AL_DEV_IN_TEST_MODE': b'\x04\x00',
            'AL_DEV_IN_STANDBY': b'\x02\x00',
            'AL_DEV_IN_DEMO_MODE': b'\x01\x00',
            'AL_NEW_ALERT': b'\x00\x08',
            b'\x80\x00': 'AL_INHIBITED',
            b'\x40\x00': 'AL_SUSPENDED',
            b'\x20\x00': 'AL_LATCHED',
            b'\x10\x00': 'AL_SILENCED_RESET',
            b'\x04\x00': 'AL_DEV_IN_TEST_MODE',
            b'\x02\x00': 'AL_DEV_IN_STANDBY',
            b'\x01\x00': 'AL_DEV_IN_DEMO_MODE',
            b'\x00\x08': 'AL_NEW_ALERT'
        }

        self.DataKeys['AlertType'] = {
            'NO_ALERT': b'\x00\x00',
            'LOW_PRI_T_AL': b'\x00\x01',
            'MED_PRI_T_AL': b'\x00\x02',
            'HI_PRI_T_AL': b'\x00\x04',
            'LOW_PRI_P_AL': b'\x01\x00',
            'MED_PRI_P_AL': b'\x02\x00',
            'HI_PRI_P_AL': b'\x04\x00',
            b'\x00\x00': 'NO_ALERT',
            b'\x00\x01': 'LOW_PRI_T_AL',
            b'\x00\x02': 'MED_PRI_T_AL',
            b'\x00\x04': 'HI_PRI_T_AL',
            b'\x01\x00': 'LOW_PRI_P_AL',
            b'\x02\x00': 'MED_PRI_P_AL',
            b'\x04\x00': 'HI_PRI_P_AL'
        }

        self.DataKeys['cal_type'] = {
            'BAR': b'\x00\x00',
            'STAIR': b'\x00\x01',
            b'\x00\x00': 'BAR',
            b'\x00\x01': 'STAIR'
        }

        self.DataKeys['MeasureMode'] = {
            'CO2_SIDESTREAM': b'\x04\x00',
            'ECG_PACED': b'\x02\x00',
            'ECG_NONPACED': b'\x01\x00',
            'ECG_DIAG': b'\x00\x80',
            'ECG_MONITOR': b'\x00\x40',
            'ECG_FILTER': b'\x00\x20',
            'ECG_MODE_EASI': b'\x00\x08',
            'ECG_LEAD_PRIMARY': b'\x00\x04',
            b'\x04\x00': 'CO2_SIDESTREAM',
            b'\x02\x00': 'ECG_PACED',
            b'\x01\x00': 'ECG_NONPACED',
            b'\x00\x80': 'ECG_DIAG',
            b'\x00\x40': 'ECG_MONITOR',
            b'\x00\x20': 'ECG_FILTER',
            b'\x00\x08': 'ECG_MODE_EASI',
            b'\x00\x04': 'ECG_LEAD_PRIMARY'
        }

        self.DataKeys['SaFixedValId'] = {
            'SA_FIX_UNSPEC': b'\x00\x00',
            'SA_FIX_INVALID_MASK': b'\x00\x01',
            'SA_FIX_PACER_MASK': b'\x00\x02',
            'SA_FIX_DEFIB_MARKER_MASK': b'\x00\x03',
            'SA_FIX_SATURATION': b'\x00\x04',
            'SA_FIX_QRS_MASK': b'\x00\x05',
            b'\x00\x00': 'SA_FIX_UNSPEC',
            b'\x00\x01': 'SA_FIX_INVALID_MASK',
            b'\x00\x02': 'SA_FIX_PACER_MASK',
            b'\x00\x03': 'SA_FIX_DEFIB_MARKER_MASK',
            b'\x00\x04': 'SA_FIX_SATURATION',
            b'\x00\x05': 'SA_FIX_QRS_MASK',
        }

        self.DataKeys['MetricState'] = {
            'METRIC_OFF': b'\x80\x00',
            b'\x80\x00': 'METRIC_OFF',
        }

        self.DataKeys['SaFlags'] = {
            'SMOOTH_CURVE': b'\x80\x00',
            'DELAYED_CURVE': b'\x40\x00',
            'STATIC_SCALE': b'\x20\x00',
            'SA_EXT_VAL_RANGE': b'\x10\x00',
            b'\x80\x00': 'SMOOTH_CURVE',
            b'\x40\x00': 'DELAYED_CURVE',
            b'\x20\x00': 'STATIC_SCALE',
            b'\x10\x00': 'SA_EXT_VAL_RANGE'
        }

        self.DataKeys['ModifyOperator'] = {
            b'\x00\x00': 'REPLACE',
            b'\x00\x01': 'ADD_VALUES',
            b'\x00\x02': 'REMOVE_VALUES',
            b'\x00\x03': 'SET_TO_DEFAULT',
            'REPLACE': b'\x00\x00',
            'ADD_VALUES': b'\x00\x01',
            'REMOVE_VALUES': b'\x00\x02',
            'SET_TO_DEFAULT': b'\x00\x03'
        }

        self.DataKeys['MeasurementState'] = {
            'INVALID': b'\x80\x00',
            'QUESTIONABLE': b'\x40\x00',
            'UNAVAILABLE': b'\x20\x00',
            'CALIBRATION_ONGOING': b'\x10\x00',
            'TEST_DATA': b'\x08\x00',
            'DEMO_DATA': b'\x04\x00',
            'VALIDATED_DATA': b'\x00\x80',
            'EARLY_INDICATION': b'\x00\x40',
            'MSMT_ONGOING': b'\x00\x20',
            'MSMT_STATE_IN_ALARM': b'\x00\x02',
            'MSMT_STATE_AL_INHIBITED': b'\x00\x01',
            b'\x80\x00': 'INVALID',
            b'\x40\x00': 'QUESTIONABLE',
            b'\x20\x00': 'UNAVAILABLE',
            b'\x10\x00': 'CALIBRATION_ONGOING',
            b'\x08\x00': 'TEST_DATA',
            b'\x04\x00': 'DEMO_DATA',
            b'\x00\x80': 'VALIDATED_DATA',
            b'\x00\x40': 'EARLY_INDICATION',
            b'\x00\x20': 'MSMT_ONGOING',
            b'\x00\x02': 'MSMT_STATE_IN_ALARM',
            b'\x00\x01': 'MSMT_STATE_AL_INHIBITED'
        }

        self.DataKeys['SimpleColour'] = {
            'COL_BLACK': b'\x00\x00',
            'COL_RED': b'\x00\x01',
            'COL_GREEN': b'\x00\x02',
            'COL_YELLOW': b'\x00\x03',
            'COL_BLUE': b'\x00\x04',
            'COL_MAGENTA': b'\x00\x05',
            'COL_CYAN': b'\x00\x06',
            'COL_WHITE': b'\x00\x07',
            'COL_PINK': b'\x00\x20',
            'COL_ORANGE': b'\x00\x35',
            'COL_LIGHT_GREEN': b'\x00\x50',
            'COL_LIGHT_RED': b'\x00\x65',
            b'\x00\x00': 'COL_BLACK',
            b'\x00\x01': 'COL_RED',
            b'\x00\x02': 'COL_GREEN',
            b'\x00\x03': 'COL_YELLOW',
            b'\x00\x04': 'COL_BLUE',
            b'\x00\x05': 'COL_MAGENTA',
            b'\x00\x06': 'COL_CYAN',
            b'\x00\x07': 'COL_WHITE',
            b'\x00\x20': 'COL_PINK',
            b'\x00\x35': 'COL_ORANGE',
            b'\x00\x50': 'COL_LIGHT_GREEN',
            b'\x00\x65': 'COL_LIGHT_RED'
        }

        self.DataKeys['MetricAccess'] = {
            'AVAIL_INTERMITTEND': b'\x80\x00',
            'UPD_PERIODIC': b'\x40\x00',
            'UPD_EPISODIC': b'\x20\x00',
            'MSMT_NONCONTINUOUS': b'\x10\x00',
            b'\x80\x00': 'AVAIL_INTERMITTEND',
            b'\x40\x00': 'UPD_PERIODIC',
            b'\x20\x00': 'UPD_EPISODIC',
            b'\x10\x00': 'MSMT_NONCONTINUOUS'
        }

        self.DataKeys['MetricCategory'] = {
            'MCAT_UNSPEC': b'\x00\x00',
            'AUTO_MEASUREMENT': b'\x00\x01',
            'MANUAL_MEASUREMENT': b'\x00\x02',
            'AUTO_SETTING': b'\x00\x03',
            'MANUAL_SETTING': b'\x00\x04',
            'AUTO_CALCULATION': b'\x00\x05',
            'MANUAL_CALCULATION': b'\x00\x06',
            'MULTI_DYNAMIC_CAPABILITIES': b'\x00\x32',
            'AUTO_ADJUST_PAT_TEMP': b'\x00\x80',
            'MANUAL_ADJUST_PAT_TEMP': b'\x00\x81',
            'AUTO_ALARM_LIMIT_SETTING': b'\x00\x82',
            b'\x00\x00': 'MCAT_UNSPEC',
            b'\x00\x01': 'AUTO_MEASUREMENT',
            b'\x00\x02': 'MANUAL_MEASUREMENT',
            b'\x00\x03': 'AUTO_SETTING',
            b'\x00\x04': 'MANUAL_SETTING',
            b'\x00\x05': 'AUTO_CALCULATION',
            b'\x00\x06': 'MANUAL_CALCULATION',
            b'\x00\x32': 'MULTI_DYNAMIC_CAPABILITIES',
            b'\x00\x80': 'AUTO_ADJUST_PAT_TEMP',
            b'\x00\x81': 'MANUAL_ADJUST_PAT_TEMP',
            b'\x00\x82': 'AUTO_ALARM_LIMIT_SETTING'
        }

        self.DataKeys['state'] = {
            'RORLS_FIRST': b'\x01',
            'RORLS_NOT_FIRST_NOT_LAST': b'\x02',
            'RORLS_LAST': b'\x03',
            b'\x01': 'RORLS_FIRST',
            b'\x02': 'RORLS_NOT_FIRST_NOT_LAST',
            b'\x03': 'RORLS_LAST'
        }

        self.DataKeys['action_type'] = {
            'NOM_ACT_POLL_MDIB_DATA': b'\x0C\x16',
            'NOM_ACT_POLL_MDIB_DATA_EXT': b'\xF1\x3B',
            b'\x0C\x16': 'NOM_ACT_POLL_MDIB_DATA',
            b'\xF1\x3B': 'NOM_ACT_POLL_MDIB_DATA_EXT'
        }

        self.DataKeys['MDSStatus'] = {
            'DISCONNECTED': b'\x00\x00',
            'UNASSOCIATED': b'\x00\x01',
            'OPERATING': b'\x00\x06',
            b'\x00\x00': 'DISCONNECTED',
            b'\x00\x01': 'UNASSOCIATED',
            b'\x00\x06': 'OPERATING'
        }

        self.DataKeys['choice'] = {
            'MDS_GEN_SYSTEM_INFO_SYSTEM_PULSE_CHOSEN': b'\x00\x01',
            b'\x00\x01': 'MDS_GEN_SYSTEM_INFO_SYSTEM_PULSE_CHOSEN'
        }

        self.DataKeys['LineFrequency'] = {
            'LIFE_F_UNSPEC': b'\x00\x00',
            'LIFE_F_50HZ': b'\x00\x01',
            'LIFE_F_60HZ': b'\x00\x02',
            b'\x00\x00': 'LIFE_F_UNSPEC',
            b'\x00\x01': 'LIFE_F_50HZ',
            b'\x00\x02': 'LIFE_F_60HZ'
        }

        self.DataKeys['ApplicationArea'] = {
            'AREA_UNSPEC': b'\x00\x00',
            'AREA_OPERATING_ROOM': b'\x00\x01',
            'AREA_INTENSIVE_CARE': b'\x00\x02',
            'AREA_NEONATAL_INTENSIVE_CARE': b'\x00\x03',
            'AREA_CARDIOLOGY_CARE': b'\x00\x04',
            b'\x00\x00': 'AREA_UNSPEC',
            b'\x00\x01': 'AREA_OPERATING_ROOM',
            b'\x00\x02': 'AREA_INTENSIVE_CARE',
            b'\x00\x03': 'AREA_NEONATAL_INTENSIVE_CARE',
            b'\x00\x04': 'AREA_CARDIOLOGY_CARE'
        }

        self.DataKeys['OperatingMode'] = {
            'OPMODE_UNSPEC': b'\x80\x00',
            'MONITORING': b'\x40\x00',
            'DEMO': b'\x20\x00',
            'SERVICE': b'\x10\x00',
            'OPMODE_STANDBY': b'\x00\x02',
            'CONFIG': b'\x00\x01',
            b'\x80\x00': 'OPMODE_UNSPEC',
            b'\x40\x00': 'MONITORING',
            b'\x20\x00': 'DEMO',
            b'\x10\x00': 'SERVICE',
            b'\x00\x02': 'OPMODE_STANDBY',
            b'\x00\x01': 'CONFIG'
        }

        self.DataKeys['PollProfileExtOptions'] = {
            'POLL1SECANDWAVEANDLISTANDDYN': b'\x8B\x00\x00\x00',
            #'POLL1SECANDWAVEANDLISTANDDYN': b'\x1B\x00\x00\x00',
            'POLL_EXT_PERIOD_NU_1SEC': b'\x80\x00\x00\x00',
            'POLL_EXT_PERIOD_NU_AVG_12SEC': b'\x40\x00\x00\x00',
            'POLL_EXT_PERIOD_NU_AVG_60SEC': b'\x20\x00\x00\x00',
            'POLL_EXT_PERIOD_NU_AVG_300SEC': b'\x10\x00\x00\x00',
            'POLL_EXT_PERIOD_RTSA': b'\x08\x00\x00\x00',
            'POLL_EXT_ENUM': b'\x04\x00\x00\x00',
            'POLL_EXT_NU_PRIO_LIST': b'\x02\x00\x00\x00',
            'POLL_EXT_DYN_MODALITIES': b'\x01\x00\x00\x00',
            b'\x80\x00\x00\x00': 'POLL_EXT_PERIOD_NU_1SEC',
            b'\x40\x00\x00\x00': 'POLL_EXT_PERIOD_NU_AVG_12SEC',
            b'\x20\x00\x00\x00': 'POLL_EXT_PERIOD_NU_AVG_60SEC',
            b'\x10\x00\x00\x00': 'POLL_EXT_PERIOD_NU_AVG_300SEC',
            b'\x08\x00\x00\x00': 'POLL_EXT_PERIOD_RTSA',
            b'\x04\x00\x00\x00': 'POLL_EXT_ENUM',
            b'\x02\x00\x00\x00': 'POLL_EXT_NU_PRIO_LIST',
            b'\x01\x00\x00\x00': 'POLL_EXT_DYN_MODALITIES',
            b'\x8B\x00\x00\x00': 'POLL1SECANDWAVEANDLISTANDDYN',
            #b'\x1B\x00\x00\x00': 'POLL1SECANDWAVEANDLISTANDDYN'
        }


        self.DataKeys['PollProfileOptions'] = {
            'P_OPT_DYN_CREATE_OBJECTS':b'\x40\x00\x00\x00',
            'P_OPT_DYN_DELETE_OBJECTS':b'\x20\x00\x00\x00',
            'P_OPT_DYN_CREATE_AND_DELETE':b'\x60\x00\x00\x00',
            b'\x40\x00\x00\x00':'P_OPT_DYN_CREATE_OBJECTS',
            b'\x20\x00\x00\x00':'P_OPT_DYN_DELETE_OBJECTS',
            b'\x60\x00\x00\x00':'P_OPT_DYN_CREATE_AND_DELETE'
        }

        self.DataKeys['max_bw_tx'] = {
            'NoEstimationPossible': b'\xFF\xFF\xFF\xFF',
            b'\xFF\xFF\xFF\xFF': 'NoEstimationPossible'
        }

        self.DataKeys['PollProfileRevision'] = {
            'POLL_PROFILE_REV_0': b'\x80\x00\x00\x00',
            b'\x80\x00\x00\x00': 'POLL_PROFILE_REV_0'
        }

        self.DataKeys['ProtocolVersion'] = {
            'MDDL_VERSION1': b'\x80\x00\x00\x00',
            b'\x80\x00\x00\x00': 'MDDL_VERSION1'
        }

        self.DataKeys['NomenclatureVersion'] = {
            'NOMEN_VERSION': b'\x40\x00\x00\x00',
            b'\x40\x00\x00\x00': 'NOMEN_VERSION',
        }

        self.DataKeys['FunctionalUnits'] = {
            'None': b'\x00\x00\x00\x00',
            b'\x00\x00\x00\x00': 'None',
        }

        self.DataKeys['SystemType'] = {
            'SYST_CLIENT': b'\x80\x00\x00\x00',
            'SYST_SERVER': b'\x00\x80\x00\x00',
            b'\x80\x00\x00\x00': 'SYST_CLIENT',
            b'\x00\x80\x00\x00': 'SYST_SERVER',
        }

        self.DataKeys['StartupMode'] = {
            'HOT_START':b'\x80\x00\x00\x00',
            'WARM_START':b'\x40\x00\x00\x00',
            'COLD_START': b'\x20\x00\x00\x00',
            b'\x80\x00\x00\x00': 'HOT_START',
            b'\x40\x00\x00\x00': 'WARM_START',
            b'\x20\x00\x00\x00': 'COLD_START',
        }

        self.DataKeys['ro_type'] = {
            b'\x00\x01':'ROIV_APDU',
            b'\x00\x02':'RORS_APDU',
            b'\x00\x03':'ROER_APDU',
            b'\x00\x05':'ROLRS_APDU',
            'ROIV_APDU': b'\x00\x01',
            'RORS_APDU': b'\x00\x02',
            'ROER_APDU': b'\x00\x03',
            'ROLRS_APDU': b'\x00\x05',
        }

        self.DataKeys['CMDType'] = {
            b'\x00\x00':'CMD_EVENT_REPORT',
            b'\x00\x01':'CMD_CONFIRMED_EVENT_REPORT',
            b'\x00\x03':'CMD_GET',
            b'\x00\x04':'CMD_SET',
            b'\x00\x05':'CMD_CONFIRMED_SET',
            b'\x00\x07':'CMD_CONFIRMED_ACTION',
            'CMD_EVENT_REPORT': b'\x00\x00',
            'CMD_CONFIRMED_EVENT_REPORT': b'\x00\x01',
            'CMD_GET': b'\x00\x03',
            'CMD_SET': b'\x00\x04',
            'CMD_CONFIRMED_SET': b'\x00\x05',
            'CMD_CONFIRMED_ACTION': b'\x00\x07',
        }

        self.DataKeys['AttributeType'] = {
            'NOM_ATTR_SYS_TYPE': 'Type',
            'NOM_ATTR_LOCALIZN': 'SystemLocal',
            'NOM_ATTR_NET_ADDR_INFO': 'IPAddressInfo',
            'NOM_ATTR_PCOL_SUPPORT': 'ProtoSupport',
            'NOM_ATTR_SYS_ID': 'VariableLabel',
            'NOM_ATTR_ID_MODEL': 'SystemModel',
            'NOM_ATTR_ID_PROD_SPECN': 'ProductionSpec',
            'NOM_POLL_PROFILE_SUPPORT': 'PollProfileSupport',
            'NOM_ATTR_POLL_PROFILE_EXT': 'PollProfileExt',
            'NOM_ATTR_ID_ASSOC_NO': 'AssociationInvokeID',
            'NOM_ATTR_NOM_VERS': 'NomenclatureVersion',
            'NOM_ATTR_MODE_OP': 'OperatingMode',
            'NOM_ATTR_AREA_APPL': 'ApplicationArea',
            'NOM_ATTR_LINE_FREQ': 'LineFrequency',
            'NOM_ATTR_STD_SAFETY': 'Safety',
            'NOM_ATTR_ALTITUDE': 'Altitude',
            'NOM_ATTR_MDS_GEN_INFO': 'MdsGenSystemInfo',
            'NOM_ATTR_VMS_MDS_STAT': 'MDSStatus',
            'NOM_ATTR_ID_BED_LABEL': 'String',
            'NOM_ATTR_TIME_ABS': 'AbsoluteTime',
            'NOM_ATTR_TIME_REL': 'RelativeTime',
            'NOM_ATTR_SYS_SPECN': 'SystemSpec',
            'NOM_ATTR_ID_HANDLE': 'Handle',
            'NOM_ATTR_ID_TYPE': 'Type',
            'NOM_ATTR_METRIC_SPECN': 'MetricSpec',
            'NOM_ATTR_ID_LABEL': 'TextId',
            'NOM_ATTR_ID_LABEL_STRING': 'String',
            'NOM_ATTR_DISP_RES': 'DispResolution',
            'NOM_ATTR_COLOR': 'SimpleColour',
            'NOM_SAT_O2_TONE_FREQ': 'PrivateAttribute',
            'NOM_ATTR_NU_VAL_OBS': 'NuObsValue',
            'NOM_ATTR_TIME_STAMP_ABS': 'AbsoluteTime',
            'NOM_ATTR_NU_CMPD_VAL_OBS': 'NuObsValCmp',
            'NOM_ATTR_TIME_PD_POLL': 'PollDataReqPeriod',
            'NOM_ATTR_POLL_NU_PRIO_LIST': 'TextIdLabel',
            'NOM_ATTR_POLL_RTSA_PRIO_LIST': 'TextIdLabel',
            'NOM_ATTR_SA_CMPD_VAL_OBS': 'SaObsValueCmp',
            'NOM_ATTR_SA_VAL_OBS': 'SaObsValue',
            'NOM_ATTR_SA_SPECN': 'SaSpec',
            'NOM_ATTR_TIME_PD_SAMP': 'RelativeTime',
            'NOM_ATTR_UNIT_CODE': 'UNITType',
            'NOM_ATTR_METRIC_STAT': 'MetricState',
            'NOM_ATTR_SCALE_SPECN_I16': 'ScaleRangeSpec16',
            'NOM_ATTR_GRID_VIS_I16': 'SaVisualGrid16',
            'NOM_ATTR_SA_FIXED_VAL_SPECN': 'SaFixedValSpec16',
            'NOM_ATTR_MODE_MSMT': 'MeasureMode',
            'NOM_ATTR_SA_CALIB_I16': 'SaCalData16',
            'NOM_ATTR_SA_RANGE_PHYS_I16': 'ScaledRange16',
            'NOM_ATTR_DEV_AL_COND': 'DeviceAlertCondition',
            'NOM_ATTR_AL_MON_P_AL_LIST': 'DevAlarmList',
            'NOM_ATTR_AL_MON_T_AL_LIST': 'DevAlarmList',
        }

        self.DataKeys['OIDType'] = self.loadOIDTypes()

        self.DataKeys['SCADAType'] = self.loadSCADATypes()

        self.DataKeys['UNITType'] = self.loadUNITTypes()

        self.DataKeys['TextId'] = self.loadPhysioLabels()

        self.DataKeys['PhysioKeys'] = self.loadPhysioKeys()

        self.DataKeys['EventTypes'] = self.loadEventTypes()

        self.DataKeys['NomPartition'] = {
            b'\x00\x01': 'NOM_PART_OBJ',
            b'\x00\x02': 'NOM_PART_SCADA',
            b'\x00\x03': 'NOM_PART_EVT',
            b'\x00\x04': 'NOM_PART_DIM',
            b'\x00\x06': 'NOM_PART_PGRP',
            b'\x00\x08': 'NOM_PART_INFRASTRUCT',
            'NOM_PART_OBJ': b'\x00\x01',
            'NOM_PART_SCADA': b'\x00\x02',
            'NOM_PART_EVT': b'\x00\x03',
            'NOM_PART_DIM': b'\x00\x04',
            'NOM_PART_PGRP': b'\x00\x06',
            'NOM_PART_INFRASTRUCT': b'\x00\x08',
        }

        self.DataKeys['Language'] = {
            b'\x00\x00': 'LANGUAGE_UNSPEC',
            b'\x00\x01': 'ENGLISH',
            'LANGUAGE_UNSPEC': b'\x00\x00',
            'ENGLISH': b'\x00\x01',
        }

        self.DataKeys['StringFormat'] = {
            b'\x00\x0B': 'STRFMT_UNICODE_NT',
            'STRFMT_UNICODE_NT': b'\x00\x0B',
        }

        self.DataKeys['ApplProtoID'] = {
            b'\x00\x01': 'AP_ID_ACSE',
            b'\x00\x05': 'AP_ID_DATA_OUT',
            'AP_ID_ACSE': b'\x00\x01',
            'AP_ID_DATA_OUT': b'\x00\x05',
        }

        self.DataKeys['TransProtoID'] = {
            b'\x00\x01': 'TP_ID_UDP',
            'TP_ID_UDP': b'\x00\x01',
        }

        self.DataKeys['ProtoOptions'] = {
            b'\x80\x00': 'P_OPT_WIRELESS',
            'P_OPT_WIRELESS': b'\x80\x00'
        }

        self.DataKeys['spec_type'] = {
            b'\x00\x00': 'UNSPECIFIED',
            b'\x00\x01': 'SERIAL_NUMBER',
            b'\x00\x02': 'PART_NUMBER',
            b'\x00\x03': 'HW_REVISION',
            b'\x00\x04': 'SW_REVISION',
            b'\x00\x05': 'FW_REVISION',
            b'\x00\x06': 'PROTOCOL_REVISION',
            'UNSPECIFIED': b'\x00\x00',
            'SERIAL_NUMBER': b'\x00\x01',
            'PART_NUMBER': b'\x00\x02',
            'HW_REVISION': b'\x00\x03',
            'SW_REVISION': b'\x00\x04',
            'FW_REVISION': b'\x00\x05',
            'PROTOCOL_REVISION': b'\x00\x06',
        }

        self.DataKeys['component_id'] = {
            b'\x00\x08': 'ID_COMP_PRODUCT',
            b'\x00\x10': 'ID_COMP_CONFIG',
            b'\x00\x18': 'ID_COMP_BOOT',
            b'\x00\x50': 'ID_COMP_MAIN_BD',
            b'\x00\x58': 'ID_COM_APPL_SW',
            'ID_COMP_PRODUCT': b'\x00\x08',
            'ID_COMP_CONFIG': b'\x00\x10',
            'ID_COMP_BOOT': b'\x00\x18',
            'ID_COMP_MAIN_BD': b'\x00\x50',
            'ID_COM_APPL_SW': b'\x00\x58',
        }

        self.DataKeys['AssocReqSessionHead'] = bytearray(b'\x0D')

        self.DataKeys['AssocReqSessionData'] = bytearray(
            b'\x05\x08\x13\x01\x00\x16\x01\x02\x80\x00\x14\x02\x00\x02')

        self.DataKeys['AssocReqPresentationHead1'] = bytearray(b'\xC1')

        self.DataKeys['AssocReqPresentationHead2'] = bytearray(
            b'\x31\x80\xA0\x80\x80\x01\x01\x00\x00\xA2\x80\xA0\x03\x00\x00\x01\xA4'
            b'\x80\x30\x80\x02\x01\x01\x06\x04\x52\x01\x00\x01\x30\x80\x06\x02\x51'
            b'\x01\x00\x00\x00\x00\x30\x80\x02\x01\x02\x06\x0C\x2A\x86\x48'
            b'\xCE\x14\x02\x01\x00\x00\x00\x01\x01\x30\x80\x06\x0C\x2A\x86'
            b'\x48\xCE\x14\x02\x01\x00\x00\x00\x02\x01\x00\x00\x00\x00\x00'
            b'\x00\x61\x80\x30\x80\x02\x01\x01\xA0\x80\x60\x80\xA1\x80\x06'
            b'\x0C\x2A\x86\x48\xCE\x14\x02\x01\x00\x00\x00\x03\x01\x00\x00'
            b'\xBE\x80\x28\x80\x06\x0C\x2A\x86\x48\xCE\x14\x02\x01\x00\x00'
            b'\x00\x01\x01\x02\x01\x02\x81')

        self.DataKeys['AssocReqPresentationTrailer'] = bytearray(
            b'\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00')

        self.DataKeys['ReleaseReq'] = bytearray(
            b'\x09\x18\xC1\x16\x61\x80\x30\x80\x02'
            b'\x01\x01\xA0\x80\x62\x80\x80\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00')

        self.MessageParameters['ReleaseRequest'] = []

        self.MessageParameters['AssociationAbort'] = []

        self.DataKeys['AssocAbort'] = bytearray(
            b'\x19\x2E\x11\x01\x03\xC1\x29\xA0\x80'
            b'\xA0\x80\x30\x80\x02\x01\x01\x06\x02'
            b'\x51\x01\x00\x00\x00\x00\x61\x80\x30'
            b'\x80\x02\x01\x01\xA0\x80\x64\x80\x80'
            b'\x01\x01\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00')

        self.DataKeys['session_id'] = {
            b'\xE1\x00': 'DataExportProtocol',
            57600: 'DataExportProtocol',
            'DataExportProtocol': b'\xE1\x00',
        }

        self.DataKeys['p_context_id'] = {
            b'\x00\x02': 'DataExportProtocol',
            'DataExportProtocol': b'\x00\x02',
        }

        self.MessageLists['ConnectIndicationEvent'] = [
            'Nomenclature',
            'ROapdus',
            'ROIVapdu',
            'EventReportArgument',
            'ConnectIndInfo',
        ]

        self.MessageLists['AssociationResponse'] = [
            'AssocRespUserData',
        ]

        self.MessageLists['AssociationRequest'] = [
            'AssocReqSessionHeader',
            'AssocReqSessionData',
            'AssocReqPresentationHeader',
            'AssocReqUserData',
            'AssocReqPresentationTrailer',
        ]

        self.MessageParameters['AssociationRequest'] = {
            'ProtocolVersion': 'MDDL_VERSION1',
            'NomenclatureVersion': 'NOMEN_VERSION',
            'FunctionalUnits': 'None',
            'SystemType': 'SYST_CLIENT',
            'StartupMode': 'HOT_START',
            'PollProfileRevision': 'POLL_PROFILE_REV_0',
            'RelativeTime': 480000,
            'max_mtu_rx': 1400,
            'max_bw_tx': 'NoEstimationPossible',
            'max_mtu_tx': 1400,
            'PollProfileOptions': 'P_OPT_DYN_CREATE_AND_DELETE',
            'PollProfileExtOptions': 'POLL1SECANDWAVEANDLISTANDDYN',
        }

        self.MessageLists['MDSCreateEvent'] = [
            'SPpdu',
            'ROapdus',
            'ROIVapdu',
            'EventReportArgument',
            'MDSCreateInfo',
        ]

        self.MessageLists['MDSCreateEventResult'] = [
            'SPpdu',
            'ROapdus',
            'RORSapdu',
            'EventReportResult',
        ]

        self.MessageLists['AssociationAbort'] = [
            'AssocAbortMsg',
        ]

        self.MessageLists['MDSSinglePollAction'] = [
            'SPpdu',
            'ROapdus',
            'ROIVapdu',
            'ActionArgument',
            'PollMdibDataReq',
        ]

        self.MessageParameters['MDSSinglePollAction'] = {
            'session_id': 'DataExportProtocol',
            'p_context_id': 'DataExportProtocol',
            'ro_type': 'ROIV_APDU',
            'invoke_id': 1,
            'CMDType': 'CMD_CONFIRMED_ACTION',
            'OIDType': ['NOM_MOC_VMS_MDS', 'NOM_MOC_VMO_AL_MON', 'NOM_ATTR_GRP_VMO_STATIC'],
            'MdsContext': 0,
            'Handle': 0,
            'action_type': 'NOM_ACT_POLL_MDIB_DATA',
            'poll_number': 1,
            'NomPartition': 'NOM_PART_OBJ',
            'scope': 0,
        }

        self.MessageLists['MDSSinglePollActionResult'] = [
            'SPpdu',
            'ROapdus',
            'RORSapdu',
            'ActionResult',
            'PollMdibDataReply',
        ]

        self.MessageLists['LinkedMDSSinglePollActionResult'] = [
            'SPpdu',
            'ROapdus',
            'ROLRSapdu',
            'ActionResult',
            'PollMdibDataReply',
        ]

        self.MessageLists['MDSExtendedPollActionNUMERIC'] = [
            'SPpdu',
            'ROapdus',
            'ROIVapdu',
            'ActionArgument',
            'PollMdibDataReqExt',
        ]

        self.MessageLists['MDSExtendedPollActionWAVE'] = [
            'SPpdu',
            'ROapdus',
            'ROIVapdu',
            'ActionArgument',
            'PollMdibDataReqExt',
        ]

        self.MessageLists['MDSExtendedPollActionALARM'] = [
            'SPpdu',
            'ROapdus',
            'ROIVapdu',
            'ActionArgument',
            'PollMdibDataReqExt',
        ]

        self.MessageParameters['MDSExtendedPollActionNUMERIC'] = {
            'session_id': 'DataExportProtocol',
            'p_context_id': 'DataExportProtocol',
            'ro_type': 'ROIV_APDU',
            'invoke_id': 1,
            'CMDType': 'CMD_CONFIRMED_ACTION',
            #OIDType: ManagedObjectID, Polled_Obj_Type, Polled_Attr_Group
            'OIDType': ['NOM_MOC_VMS_MDS', 'NOM_MOC_VMO_METRIC_NU', 'ALL'],
            'MdsContext': 0,
            'Handle': 0,
            'action_type': 'NOM_ACT_POLL_MDIB_DATA_EXT',
            'poll_number': 1,
            'NomPartition': 'NOM_PART_OBJ',
            'scope': 0,
            'RelativeTime': 800000,
        }

        self.MessageParameters['MDSExtendedPollActionWAVE'] = {
            'session_id': 'DataExportProtocol',
            'p_context_id': 'DataExportProtocol',
            'ro_type': 'ROIV_APDU',
            'invoke_id': 1,
            'CMDType': 'CMD_CONFIRMED_ACTION',
            #OIDType: ManagedObjectID, Polled_Obj_Type, Polled_Attr_Group
            'OIDType': ['NOM_MOC_VMS_MDS', 'NOM_MOC_VMO_METRIC_SA_RT', 'ALL'],
            'MdsContext': 0,
            'Handle': 0,
            'action_type': 'NOM_ACT_POLL_MDIB_DATA_EXT',
            'poll_number': 1,
            'NomPartition': 'NOM_PART_OBJ',
            'scope': 0,
            'RelativeTime': 800000,
        }

        self.MessageParameters['MDSExtendedPollActionALARM'] = {
            'session_id': 'DataExportProtocol',
            'p_context_id': 'DataExportProtocol',
            'ro_type': 'ROIV_APDU',
            'invoke_id': 1,
            'CMDType': 'CMD_CONFIRMED_ACTION',
            #OIDType: ManagedObjectID, Polled_Obj_Type, Polled_Attr_Group
            'OIDType': ['NOM_MOC_VMS_MDS', 'NOM_MOC_VMO_AL_MON', 'ALL'],
            'MdsContext': 0,
            'Handle': 0,
            'action_type': 'NOM_ACT_POLL_MDIB_DATA_EXT',
            'poll_number': 1,
            'NomPartition': 'NOM_PART_OBJ',
            'scope': 0,
            'RelativeTime': 800000,
        }

        self.MessageLists['MDSExtendedPollActionResult'] = [
            'SPpdu',
            'ROapdus',
            'RORSapdu',
            'ActionResult',
            'PollMdibDataReplyExt',
        ]

        self.MessageLists['ReleaseRequest'] = {
            'ReleaseRequested',
        }

        self.MessageLists['LinkedMDSExtendedPollActionResult'] = [
            'SPpdu',
            'ROapdus',
            'ROLRSapdu',
            'ActionResult',
            'PollMdibDataReplyExt',
        ]

        self.MessageLists['MDSGetPriorityList'] = [
            'SPpdu',
            'ROapdus',
            'ROIVapdu',
            'GetArgument',
        ]

        self.MessageParameters['MDSGetPriorityList'] = {
            'session_id': 'DataExportProtocol',
            'p_context_id': 'DataExportProtocol',
            'ro_type': 'ROIV_APDU',
            'invoke_id': 1,
            'CMDType': 'CMD_GET',
            'OIDType':  ['NOM_MOC_VMS_MDS'],
            'MdsContext': 0,
            'Handle': 0,
            'scope':0,
        }

        self.MessageLists['MDSGetPriorityListResult'] = [
            'SPpdu',
            'ROapdus',
            'RORSapdu',
            'GetResult',
        ]

        self.MessageLists['MDSSetPriorityListWAVE'] = [
            'SPpdu',
            'ROapdus',
            'ROIVapdu',
            'SetArgument',
        ]

        self.MessageLists['MDSSetPriorityListNUMERIC'] = [
            'SPpdu',
            'ROapdus',
            'ROIVapdu',
            'SetArgument',
        ]

        self.MessageParameters['MDSSetPriorityListWAVE'] = {
            'session_id': 'DataExportProtocol',
            'p_context_id': 'DataExportProtocol',
            'ro_type': 'ROIV_APDU',
            'invoke_id': 1,
            'CMDType': 'CMD_CONFIRMED_SET',
            'OIDType':  ['NOM_MOC_VMS_MDS', 'NOM_ATTR_POLL_RTSA_PRIO_LIST'],
            'MdsContext': 0,
            'Handle': 0,
            'scope': 0,
            'ModifyOperator': 'REPLACE',
            'count': 1,
            'TextIdLabel': [],
        }

        self.MessageParameters['MDSSetPriorityListNUMERIC'] = {
            'session_id': 'DataExportProtocol',
            'p_context_id': 'DataExportProtocol',
            'ro_type': 'ROIV_APDU',
            'invoke_id': 1,
            'CMDType': 'CMD_CONFIRMED_SET',
            'OIDType':  ['NOM_MOC_VMS_MDS', 'NOM_ATTR_POLL_NU_PRIO_LIST'],
            'MdsContext': 0,
            'Handle': 0,
            'scope': 0,
            'ModifyOperator': 'REPLACE',
            'count': 1,
            'TextIdLabel': [],
        }

        self.MessageLists['MDSSetPriorityListResult'] = [
            'SPpdu',
            'ROapdus',
            'RORSapdu',
            'SetResult',
        ]

    # Returns value from uint32 binary
    def get32(self, data):
        return struct.unpack('>I',data)[0]

    # Returns value from uint16 binary
    def get16(self, data):
        return struct.unpack('>H',data)[0]

    # Returns value from int16 binary
    def geti16(self, data):
        return struct.unpack('>h',data)[0]

    # Returns value from uint8 binary
    def get8(self, data):
        return struct.unpack('>B',data)[0]

    # Returns uint32 binary from value
    def set32(self, data):
        return bytearray(struct.pack('>I',data))

    # Returns uint16 binary from value
    def set16(self, data):
        return bytearray(struct.pack('>H',data))

    # Returns uint8 binary from value
    def set8(self, data):
        return bytearray(struct.pack('>B',data))

    # Reads in text file of OID Types into a bidirectional dictionary
    # with the format number:label and label:number, returns dict
    def loadOIDTypes(self):
        """
        Creates a dictionary from the txt file OIDTypes.txt with label: number
        and number: label

        OIDTypes.txt is organized [label number] (in each line)
        """

        oid_file = open(os.path.join(package_directory,"OIDTypes.txt"),"r")
        labels = []
        numbers = []

        for line in oid_file:

            split_line = line.split()

            labels.append(split_line[0])
            numbers.append(bytes(self.set16(int(split_line[1]))))

        OID_Type_Dict = dict(zip(numbers, labels))
        OID_Type_Reverse_Dict = dict(zip(labels, numbers))

        OID_Type = OID_Type_Dict.copy()
        OID_Type.update(OID_Type_Reverse_Dict)

        logging.debug("OIDType Dict: {0}".format(OID_Type))

        oid_file.close()

        return OID_Type

    # Reads in text file of Event Types into a bidirectional dictionary
    # with the format number:label and label:number, returns dict
    def loadEventTypes(self):
        """
        Creates a dictionary from the txt file OIDTypes.txt with label: number
        and number: label

        EventTypes.txt is organized [label number] (in each line)
        """

        event_file = open(os.path.join(package_directory,"EventTypes.txt"),"r")
        labels = []
        numbers = []

        for line in event_file:

            split_line = line.split()

            labels.append(split_line[0])
            numbers.append(int(split_line[1]))

        Event_Type_Dict = dict(zip(numbers,labels))
        Event_Type_Reverse_Dict = dict(zip(labels,numbers))

        Event_Type = Event_Type_Dict.copy()
        Event_Type.update(Event_Type_Reverse_Dict)

        event_file.close()

        return Event_Type

    # Reads in text file of SCADA Types into a bidirectional dictionary
    # with the format number:label and label:number, returns dict
    def loadSCADATypes(self):
        """
        Creates a dictionary from the txt file SCADATypes.txt with label: number
        and number: label

        SCADATypes.txt is organized [label number] (in each line)
        """

        scada_file = open(os.path.join(package_directory,"SCADATypes.txt"),"r")
        labels = []
        numbers = []

        for line in scada_file:

            split_line = line.split()

            labels.append(split_line[0])
            numbers.append(bytes(self.set16(int(split_line[1]))))

        SCADA_Type_Dict = dict(zip(numbers,labels))
        SCADA_Type_Reverse_Dict = dict(zip(labels,numbers))

        SCADA_Type = SCADA_Type_Dict.copy()
        SCADA_Type.update(SCADA_Type_Reverse_Dict)

        scada_file.close()

        return SCADA_Type

    # Reads in text file of Unit Types into a bidirectional dictionary
    # with the format number:label and label:number, returns dict
    def loadUNITTypes(self):
        """
        Creates a dictionary from the txt file UNITTypes.txt with
        unit:number and number:unit

        UNITTypes.txt is organized
        line 1: label number
        line 2: unit
        """

        unit_file = open(os.path.join(package_directory,"UNITTypes.txt"),"r")
        labels = []
        numbers = []
        units = []

        for line in unit_file:
            if line.startswith(u'NOM_DIM'):

                split_line = line.split()

                labels.append(split_line[0])
                numbers.append(bytes(self.set16(int(split_line[1]))))
            else:
                line = line.rstrip()
                units.append(line)

        Unit_Type_Dict = dict(zip(numbers,units))
        Unit_Type_Reverse_Dict = dict(zip(units,numbers))

        Unit_Type = Unit_Type_Dict.copy()
        Unit_Type.update(Unit_Type_Reverse_Dict)

        unit_file.close()

        return Unit_Type

    # Reads in text file of PhysioLabels into a bidirectional dictionary
    # with the format description:binary, symbol:binary, and binary:description
    def loadPhysioLabels(self):
        """
        Creates a dictionary from the txt file Physiolabels.txt with
        label:number and number:label

        This will load all of the textIdLabels such that one can look through
        based on the description or symbol, and reading output from the
        monitor will return the description.

        For example: CPP - 0x00025804, Cerebral Perfusion Pressure - 0x00025804
                     and 0x00025804 - Cerebral Perfusion Pressure is one
                     set of entries in the dict
        """

        # Derek: Changed file encoding to UTF-8 for Py2 compatibility
        with open(os.path.join(package_directory, "PhysioLabels.txt"), "r") as label_file:

            labels = []
            descriptions = []
            numbers = []

            # logging.debug('Opened label file {0}'.format(label_file))

            current_line = ''
            for line in label_file:

                # logging.debug('Looking at line: {0}'.format(line.rstrip()))

                previous_line = current_line
                current_line = line

                if current_line.startswith('Label:'):

                    # Storing labels
                    split_label_line = previous_line.split()

                    # Some labels are the descriptors
                    if len(split_label_line) == 1:
                        labels.append(split_label_line[0])
                        descriptions.append(split_label_line[0])

                    # Special case where L has descriptor after in label
                    elif split_label_line[0] == 'L':
                        labels.append(' '.join(split_label_line[0:2]))
                        descriptions.append(' '.join(split_label_line[2:-1] + [split_label_line[-1]]))

                    # Lots of specifiers in label (ie 'l','r', or 'number')
                    elif len(split_label_line[1]) == 1:

                        labels.append(' '.join(split_label_line[0:2]))
                        descriptions.append(' '.join(split_label_line[2:-1] + [split_label_line[-1]]))

                    # Every other case
                    else:
                        labels.append(split_label_line[0])
                        descriptions.append(' '.join(split_label_line[1:-1]  + [split_label_line[-1]]))

                if current_line.startswith('NLS_'):

                    # Storing binary value
                    split_line = current_line.split()
                    numbers.append(codecs.decode(split_line[1][2:10], 'hex'))

            Label_Dict = dict(zip(numbers, descriptions))
            Label_Reverse_Dict = dict(zip(labels, numbers))
            Label_Reverse_Dict2 = dict(zip(descriptions, numbers))

            Label = Label_Dict.copy()
            Label.update(Label_Reverse_Dict)
            Label.update(Label_Reverse_Dict2)

        logging.debug('Labels: {0}'.format(Label))

        return Label

    # Reads in text file of Physiolabels into a dictionary with the format
    # description:labels (for creating Numpy arrays)
    def loadPhysioKeys(self):
        """
        Creates a dictionary from the txt file Physiolabels.txt with
        Physio Label: SCADA Type(s)

        Important for initializing Numpy arrays from the MDSGetPriorityListResult

        For example: Cerebral Perfusion Pressure - NOM_PRESS_CEREB_PERF
        """

        label_file = open(os.path.join(package_directory,"PhysioLabels.txt"),"r")
        descriptions = [];
        scadas = []

        current_line = label_file.readline()

        while(current_line):

            previous_line = current_line
            current_line = label_file.readline()

            # Read in scada types
            individual_scada = []
            while current_line.startswith('Label:') == 0 and current_line:

                if current_line.startswith('NOM') and current_line.startswith('NOM_DIM') == 0:
                    individual_scada.append(current_line.split()[0])
                previous_line = current_line
                current_line = label_file.readline()

            if individual_scada or scadas:
                scadas.append(individual_scada)

            if current_line.startswith('Label:'):

                split_label_line = previous_line.split()

                # Some labels are the descriptors
                if len(split_label_line) == 1:
                    descriptions.append(split_label_line[0])

                # Special case where L has descriptor after in label
                elif split_label_line[0] == 'L':
                    descriptions.append(' '.join(split_label_line[2:-1] + [split_label_line[-1]]))

                # Lots of specifiers in label (ie 'l','r', or 'number')
                elif len(split_label_line[1]) == 1:
                    descriptions.append(' '.join(split_label_line[2:-1] + [split_label_line[-1]]))

                # Every other case
                else:
                    descriptions.append(' '.join(split_label_line[1:-1]  + [split_label_line[-1]]))

        Label_Dict = dict(zip(descriptions, scadas))

        label_file.close()

        return Label_Dict

    # Reads in AttributeLists, returns index
    def readAttributeList(self, index, current_message_dict, data):
        """
        Reads in AttributeLists
        """
        # Initialize Variables
        current_message_dict['AttributeList'] = {}
        current_message_dict['AttributeList']['count'] = self.get16(data[index: index+2])
        current_message_dict['AttributeList']['length'] = self.get16(data[index+2: index+4])
        current_message_dict['AttributeList']['AVAType'] = {}

        index += 4

        # Deal with Null Attributes
        if current_message_dict['AttributeList']['count'] == 0:
            current_message_dict['AttributeList']['AVAType'] = 'Null'

        else:

            # Iterate through "count" attributes
            for i in range(current_message_dict['AttributeList']['count']):

                OIDIndex = data[index:index+2]

                if OIDIndex == b'\x00\x01':
                    OIDType = 'NOM_POLL_PROFILE_SUPPORT'
                elif OIDIndex == b'\x01\x02':
                    OIDType = 'NOM_MDIB_OBJ_SUPPORT'
                elif OIDIndex == b'\xF0\x01':
                    OIDType = 'NOM_ATTR_POLL_PROFILE_EXT'
                # Fix from @uday for u'ALL' problem 3/18
                elif OIDIndex == b'\x00\x00':
                    OIDType = 0
                else:
                    # This is the real dictionary, incorporate partitions somehow
                    OIDType = self.DataKeys['OIDType'].get(OIDIndex, OIDIndex)

                # length
                length = self.get16(data[index+2:index+4])
                index += 4

                # Initialize AVAType variables
                current_message_dict['AttributeList']['AVAType'][OIDType] = {}
                current_message_dict['AttributeList']['AVAType'][OIDType]['length'] = length
                current_message_dict['AttributeList']['AVAType'][OIDType]['AttributeValue'] = {}

                # If OIDType is defined, then iterate through the OIDType

                # logging.debug("OIDType: {0} ({1})".format(OIDType, type(OIDType)))
                # Changed in Py3 vs Py27 -- it is always a string, need to check for unicode
                if isinstance(OIDType, unicode):
                    # logging.debug("Adding OIDType")

                    AttributeType = self.DataKeys['AttributeType'].get(OIDType, OIDType)

                    current_message_dict_OID = current_message_dict['AttributeList']['AVAType'][OIDType]['AttributeValue']

                    index = self.recurseRead([AttributeType], index, current_message_dict_OID, data)

                # Otherwise, just keep the number as a placeholder and add to the index appropriately
                else:

                    # logging.debug("Skipping OIDType")
                    current_message_dict['AttributeList']['AVAType'][OIDType]['AttributeValue'] = 'OIDType Not Defined'
                    index += length

        return index

    # Reads in data types of format [count, length, value[1]], returns index
    def readVariableLengthList(self, index, data_type, current_message_dict, data):
        """
        Reads in data types with various "counts"
        """

        # Initialize Variables
        current_message_dict[data_type] = {}
        current_message_dict[data_type]['count'] = self.get16(data[index: index+2])
        current_message_dict[data_type]['length'] = self.get16(data[index+2: index+4])
        index += 4

        # Initialize data_value
        data_value = self.DataTypes[data_type][2]

        # Iterate through "count" times, and generate values each time
        for i in range(current_message_dict[data_type]['count']):

            current_message_dict[data_type][data_value + '_' + str(i)] = {}
            current_message_dict_count = current_message_dict[data_type][data_value + '_' + str(i)]

            index = self.recurseRead([data_value], index, current_message_dict_count, data)

        return index

    # Reads in data types of format [length, value[length uint8s]], returns index
    def readVariableLabel(self, index, current_message_dict, data):
        """
        Reads in VariableLabels
        """

        # Initialize Variables
        current_message_dict['VariableLabel'] = {}
        current_message_dict['VariableLabel']['length'] = self.get16(data[index: index+2])
        current_message_dict['VariableLabel']['value'] = []
        index += 2

        # Read through the values "length" times
        for i in range(current_message_dict['VariableLabel']['length']):

            current_message_dict['VariableLabel']['value'].append(self.get8(data[i:i+1]))
            index += 1

        return index

    # Reads in data types of format [length, value[length uint16s]], returns index
    def readVariableData(self, index, current_message_dict, data):
        """
        Reads in VariableData (ie actual data values of uint16s)
        """

        # Initialize Variables
        current_message_dict['VariableData'] = {}
        current_message_dict['VariableData']['length'] = self.get16(data[index: index+2])
        current_message_dict['VariableData']['value'] = []
        index += 2

        # Read through the values "length" times
        for i in range(int(current_message_dict['VariableData']['length']/2)):

            current_message_dict['VariableData']['value'].append(self.get16(data[index: index+2]))
            index += 2

        return index

    # Reads in data types of string format, returns index
    def readString(self, index, current_message_dict, data):
        """
        Reads in Strings
        dumbest formatting ever - utf-16, and each of the two bytes in order
        has to be swapped
        """
        # Initialize Variables
        current_message_dict['String'] = {}
        current_message_dict['String']['length'] = self.get16(data[index: index+2])

        index += 2

        byte_values = data[index:index+current_message_dict['String']['length']]
        current_message_dict['String']['value'] = ''

        for i in range(0, int(current_message_dict['String']['length']/2), 1):
            temp = byte_values[2*i+1:2*i+2] + byte_values[2*i:2*i+1]
            current_message_dict['String']['value'] += temp.decode('utf-16', errors='ignore')

        current_message_dict['String']['value'] = current_message_dict['String']['value'].split(' ')[0]

        # if current_message_dict.get('String').get('value'):
        #     logging.debug(current_message_dict.get('String').get('value'))

        index += current_message_dict['String']['length']
        return index

    # Reads in data types of FLOAT format, returns index
    def readFLOAT(self, index, current_message_dict, data):
        """
        Reads in Floats
        """
        # Initialize Variables
        current_message_dict['FLOATType'] = {}

        # Check for exceptions
        if data[index+1:index+4] == b'\x7F\xFF\xFF':
            current_message_dict['FLOATType'] = 'Not a number'

        elif data[index+1:index+4] == b'\x80\x00\x00':
            current_message_dict['FLOATType'] = 'Not at this resolution'

        elif data[index+1:index+4] ==b'\x7F\xFF\xFE':
            current_message_dict['FLOATType'] = 'Positive Infinity'

        elif data[index+1:index+4] ==b'\x80\x00\x02':
            current_message_dict['FLOATType'] = 'Negative Infinity'

        else:
            exponent = struct.unpack('>b',data[index:index+1])[0]
            (num1, num2, num3) = struct.unpack('>BBB', data[index+1:index+4])
            mantissa = (num1*65536)+(num2*256)+num3
            if mantissa >= 0x800000:
                mantissa -= 0x1000000

            current_message_dict['FLOATType'] = mantissa * 10 ** exponent

        index += 4

        return index

    # Read in data type of al_source_code, returns index
    def readAlSourceCode(self, index, current_message_dict, data):
        """
        Reads in DevAlarmEntry
        """
        # Store source
        source = data[index:index+2]
        index += 2

        # Store and determine code (ignoring last bit)
        # converting bc event types has binary keys
        code = self.get16(data[index:index+2])
        index += 2

        # Based on code, determine source in OID or SCADA
        if code & 1:
            if source in self.DataKeys['OIDType']:
                current_message_dict['al_source'] = self.DataKeys['OIDType'][source]
            else:
                current_message_dict['al_source'] = self.get16(source)
        else:
            if source in self.DataKeys['SCADAType']:
                current_message_dict['al_source'] = self.DataKeys['SCADAType'][source]
            else:
                current_message_dict['al_source'] = self.get16(source)

        # Set code to bytes to iterate through EventTypes, turn off last bit
        code = code & ~1
        if code in self.DataKeys['EventTypes']:
            current_message_dict['al_code'] = self.DataKeys['EventTypes'][code]
        else:
            current_message_dict['al_code'] = code

        return index

    # Iterates recursively through data structure, returns index
    def recurseRead(self, message_list, index, current_message_dict, data):
        """
        Inputs:
        message_list: A list of the data types stored in the message
        index: The current index being parsed
        current_message_dict: A dictionary created to store the data
        data: UDP data packet

        Output:
        index: updates the index after each loop
        """

        # Iterate through each data type in the list
        for data_type in message_list:

            # This is primarily to ensure lists accompanying "AttributeLists"
            # aren't iterated through
            if type(data_type) != list:

                # Because length_ has appended data
                if 'ASNLength' in data_type or 'LILength' in data_type or 'length' in data_type:

                    index = self.readLengths(index, current_message_dict, data, data_type)

                # AttributeList needs separate parser
                elif data_type == 'AttributeList':

                    index = self.readAttributeList(index, current_message_dict, data)

                # VariableLabel needs separate parser
                elif data_type == 'VariableLabel':

                    index = self.readVariableLabel(index, current_message_dict, data)

                # VariableData needs separate parser
                elif data_type == 'VariableData':

                    index = self.readVariableData(index, current_message_dict, data)

                # String needs separate parser
                elif data_type == 'String':

                    index = self.readString(index, current_message_dict, data)

                # FLOATType needs separate parser
                elif data_type == 'FLOATType':

                    index = self.readFLOAT(index, current_message_dict, data)

                # al_source_code needs separate parser
                elif data_type == 'al_source_code':

                    index = self.readAlSourceCode(index, current_message_dict, data)

                # VariableLengthList needs separate parser
                elif self.DataTypes[data_type][0] == 'count':

                    index = self.readVariableLengthList(index, data_type, current_message_dict, data)

                # If there is an integer (ie got to basic data type)
                elif type(self.DataTypes[data_type][0]) == int:

                    # Read out uint32
                    if self.DataTypes[data_type][0] == 32:
                        bit_range = data[index:index+4]
                        index += 4

                    # Read out uint16
                    elif self.DataTypes[data_type][0] == 16:

                        bit_range = data[index:index+2]
                        index += 2

                    # Read out int16 (note: only 1 case)
                    elif self.DataTypes[data_type][0] == -16:
                        current_message_dict[data_type] = self.geti16(data[index:index+2])
                        index += 2
                        bit_range = b''

                    # for uint8s there is a second value indicating how many uint8s there are
                    elif self.DataTypes[data_type][0] == 8:

                        # Deal with BCD encoding
                        if self.DataTypes[data_type][1] == 'bcd':
                            bit_range = b''
                            temp_value = self.get8(data[index:index+1])
                            temp_bin = '{0:08b}'.format(temp_value)
                            digit_one = int(temp_bin[0:4],2)
                            digit_two = int(temp_bin[4:8],2)
                            value = int(str(digit_one) + str(digit_two))
                            current_message_dict[data_type] = value
                            index += 1

                        elif self.DataTypes[data_type][1] == 1:
                            bit_range = data[index:index+1]
                            index += 1

                        else:
                            bit_range = []
                            for i in range(self.DataTypes[data_type][1]):
                                bit_range.append(self.get8(data[index:index+1]))
                                index += 1

                    # If there is a key associated with the int
                    # store the value in the created dictionary
                    if self.DataKeys.get(data_type, 'Not Defined') != 'Not Defined':

                        current_message_dict[data_type] = self.DataKeys[data_type].get(bit_range,bit_range)

                        # If bytes, then convert to int
                        if type(current_message_dict[data_type]) == bytes:

                            if len(bit_range) == 4:

                                current_message_dict[data_type] = self.get32(bit_range)

                            elif len(bit_range) == 2:

                                current_message_dict[data_type] = self.get16(bit_range)

                    # Otherwise just store the values
                    elif len(bit_range) == 4 and type(bit_range) == bytes:

                        current_message_dict[data_type] = self.get32(bit_range)

                    elif len(bit_range) == 2 and type(bit_range) == bytes:

                        current_message_dict[data_type] = self.get16(bit_range)

                    elif len(bit_range) == 1 and type(bit_range) == bytes:

                        current_message_dict[data_type] = self.get8(bit_range)

                    elif bit_range != b'':

                        current_message_dict[data_type] = bit_range

                # If not a basic data type, than reiterate through with the
                # next level of the data tree
                else:

                    current_message_dict[data_type] = {}
                    index = self.recurseRead(self.DataTypes[data_type], index, current_message_dict[data_type], data)

        return index

    # Main function to read in messages, returns dictionary
    def readData(self,data):

        # Determine message type
        message_type = self.getMessageType(data)

        # Print out Message Type
        #print('Reading in ' + message_type + '...')

        # Load in list defining data types in message
        current_message_list = self.MessageLists[message_type]

        # Initialize dictionary based on message
        current_message_dict = {}

        # Initialize index
        if (message_type == 'AssociationResponse'):
            index = data.find(b'\xBE\x80\x28\x80\x02\x01\x02\x81') + 8

        else:
            index = 0

        # Recursively read the message
        if message_type != 'AssociationAbort':
            finalIndex = self.recurseRead(current_message_list, index, current_message_dict, data)
        else:
            current_message_dict['AssociationAbort'] = ''

        # Output port for ConnectIndicationEvent
        if message_type == 'ConnectIndicationEvent':
            IP = current_message_dict['ConnectIndInfo']['AttributeList']['AVAType']['NOM_ATTR_NET_ADDR_INFO']['AttributeValue']['IPAddressInfo']['IPAddress']
            IPAddress = str(IP[0]) + '.' + str(IP[1]) + '.' + str(IP[2]) + '.' + str(IP[3])

            return current_message_dict, current_message_dict['ConnectIndInfo']['AttributeList']['AVAType']['NOM_ATTR_PCOL_SUPPORT']['AttributeValue']['ProtoSupport']['ProtoSupportEntry_3']['ProtoSupportEntry']['port_number'], IPAddress
        # Output parameters necessary for MDSCreateEventResult
        elif message_type == 'MDSCreateEvent':

            logging.debug("MDSCreateEvent->message_dict: {0}".format(current_message_dict))

            params = {'session_id': current_message_dict['SPpdu']['session_id'],
                'p_context_id': current_message_dict['SPpdu']['p_context_id'],
                'ro_type': 'RORS_APDU',
                'invoke_id': current_message_dict['ROIVapdu']['invoke_id'],
                'CMDType': current_message_dict['ROIVapdu']['CMDType'],
                'OIDType': [current_message_dict['EventReportArgument']['ManagedObjectID']['OIDType'], current_message_dict['EventReportArgument']['OIDType']],
                'MdsContext': current_message_dict['EventReportArgument']['ManagedObjectID']['GlbHandle']['MdsContext'],
                'Handle': current_message_dict['EventReportArgument']['ManagedObjectID']['GlbHandle']['Handle'],
                'RelativeTime': current_message_dict['EventReportArgument']['RelativeTime']}
            logging.debug("MDSCreateEvent->params: {0}".format(params))

            return current_message_dict, params

        else:
            return current_message_dict

    # Reads lengths, ASNLengths, LILengths into messages, no return
    def readLengths(self, index, current_message_dict, data, data_type):
        """
        Because lengths have varied definitions depending on their size, need
        separate function to read them in
        """

        if ('ASNLength' in data_type):

            if (self.get8(data[index:index+1]) == 130):
                current_message_dict['ASNLength'] = self.get16(data[index+1:index+3])
                index += 3

            elif (self.get8(data[index:index+1]) == 129):
                current_message_dict['ASNLength'] = self.get8(data[index+1:index+2])
                index += 2

            else:
                current_message_dict['ASNLength'] = self.get8(data[index:index+1])
                index += 1


        elif ('LILength' in data_type):

            if (self.get8(data[index:index+1]) == 255):
                current_message_dict['LILength'] = self.get16(data[index+1:index+3])
                index += 3

            else:
                current_message_dict['LILength'] = self.get8(data[index:index+1])
                index += 1

        elif ('length' in data_type):

            current_message_dict['length'] = self.get16(data[index:index+2])
            index += 2

        return index

    # Writes lengths, ASNLengths, LILengths into messages, no return
    def writeLengths(self, output_message, length, ASNLength, LILength, finalIndex):
        """
        Because lengths must be calculated after the fact, this uses length,
        ASNLength, and LILength which stores the index where the value is
        located and the end index that the length value must retain (ie
        end index - start index)
        """

        # Initialize variables
        start_index = []
        end_index = []

        start_index_asn = []
        end_index_asn = []
        asn_indicator = []

        start_index_LI = []
        end_index_LI = []
        LI_indicator = []

        # Add final values for length_final, ASNLength_final, and LILength_final
        for keys in length.keys():

            if 'final' in keys:

                length[keys].append(finalIndex-1)

        for keys in ASNLength.keys():

            if 'final' in keys:

                ASNLength[keys].append(finalIndex-1)

        for keys in LILength.keys():

            if 'final' in keys:

                LILength[keys].append(finalIndex-1)


        # Iterate through and extract all the data into tuples
        for values in length.values():
            start_index.append(values[0])
            end_index.append(values[1])

        for values in ASNLength.values():
            start_index_asn.append(values[0])
            end_index_asn.append(values[1])
            asn_indicator.append('asn')

        for values in LILength.values():
            start_index_LI.append(values[0])
            end_index_LI.append(values[1])
            LI_indicator.append('LI')


        lengths = list(zip(start_index, end_index))
        asn = list(zip(start_index_asn, end_index_asn, asn_indicator))
        LI = list(zip(start_index_LI, end_index_LI, LI_indicator, LI_indicator))
        all_lengths = lengths + asn + LI

        # Sort the data with highest indices first
        all_lengths_sorted = sorted(all_lengths, reverse = True)

        # Iterate through the tuples, and edit output_message accordingly
        for index,tuples in enumerate(all_lengths_sorted):

            # length is end_index - start_index
            length = tuples[1] - tuples[0]

            # if its ASNLength need to follow this method:
            if len(tuples) == 3:
                if length <= 127:
                    output_message[tuples[0]] = length

                elif length > 127 and length <= 255:
                    output_message[tuples[0]] = 129
                    output_message.insert(tuples[0]+1,length)

                    for add_tuples in all_lengths_sorted[index+1:len(all_lengths_sorted)]:
                        list_add_tuples = list(add_tuples)
                        list_add_tuples[1] += 1
                        add_tuples = tuple(list_add_tuples)
                else:
                    byte = self.set16(length)
                    output_message[tuples[0]] = 130
                    output_message.insert(tuples[0]+1,byte[0])
                    output_message.insert(tuples[0]+2,byte[1])

                    # Update lengths if change in size of bytes
                    for add_tuples in all_lengths_sorted[index+1:len(all_lengths_sorted)]:
                        list_add_tuples = list(add_tuples)
                        list_add_tuples[1] += 2
                        add_tuples = tuple(list_add_tuples)

            # if its LILength need to follow this method:
            elif len(tuples) == 4:

                if length <= 254:
                    output_message[tuples[0]] = length

                else:
                    byte = self.set16(length)
                    output_message[tuples[0]] = 255
                    output_message.insert(tuples[0]+1, byte[0])
                    output_message.insert(tuples[0]+2, byte[1])

                    for add_tuples in all_lengths_sorted[index+1:len(all_lengths_sorted)]:
                        list_add_tuples = list(add_tuples)
                        list_add_tuples[1] += 2
                        add_tuples = tuple(list_add_tuples)

            # Normal length uint16
            else:
                byte = self.set16(length-1)
                output_message[tuples[0]] = byte[0]
                output_message[tuples[0]+1] = byte[1]

    # Writes AttributeLists
    def writeAttributeList(self, message_list, output_message, length, ASNLength, LILength, index, parameters):

        # Handle Null Attributes
        if message_list[1][0] == 'Null':
            output_message += b'\x00\x00\x00\x00'
            index += 4

        else:
            # count
            output_message += self.set16(len(message_list[1]))
            index += 2

            # length (stored to be calculated later)
            # takes the name of the last value in the list and appends it to
            # length, so when it is done parsing length can be calculated
            length[self.DataKeys['AttributeType'].get(message_list[1][len(message_list[1])-1]) + '_' + str(index)] = [index]
            output_message += bytearray(b'\xFF\xFF')
            index += 2


            #AVAType
            for data_type in message_list[1]:

                # OIDType
                if (data_type == 'NOM_POLL_PROFILE_SUPPORT'):
                    output_message += self.set16(1)
                elif (data_type == 'NOM_MDIB_OBJ_SUPPORT'):
                    output_message += self.set16(258)
                elif (data_type == 'NOM_ATTR_POLL_PROFILE_EXT'):
                    output_message += self.set16(61441)
                else:
                    output_message += self.DataKeys['OIDType'][message_list[1][0]]
                index += 2

                # length
                AttributeType = self.DataKeys['AttributeType'].get(data_type)
                length[AttributeType + '_' + str(index)] = [index]
                output_message += bytearray(b'\xFF\xFF')
                index += 2

                # AttributeValue
                index = self.recurseWrite([AttributeType], output_message, length, ASNLength, LILength, index, parameters)

        return index

    # Writes AttributeIdLists
    def writeAttributeIdList(self, message_list, output_message, length, ASNLength, LILength, index, parameters):

        # count
        output_message += self.set16(len(message_list[1]))
        index += 2

        # length
        length = 2*len(message_list[1])
        output_message += self.set16(length)
        index += 2

        #OIDValue
        for data_type in message_list[1]:

            # OIDType
            output_message += self.DataKeys['OIDType'][data_type]
            index += 2

        return index

    # Main function to write messages, outputs bytes
    def writeData(self, message_type, *parameter_input):

        # Load in list defining data types in message
        message_list = self.MessageLists[message_type]

        # Check if parameters input, otherwise use default
        # parameters should be a dictionary with key as the data type and the
        # value as the specification
        if self.MessageParameters.get(message_type,'null') == 'null':
            parameters = copy.deepcopy(parameter_input[0])

        else:
            parameters = copy.deepcopy(self.MessageParameters[message_type])
            if (parameter_input):
                parameters.update(parameter_input[0])


        # Initialize message list to send
        output_message = bytearray()

        # Dictionary to store all the individual parts of the message
        length = {}
        LILength = {}
        ASNLength = {}
        index = 0

        if parameters == []:
            parameters = {}
        logging.debug("Write data->parameters: {0}".format(parameters))
        logging.debug("Write data->message list: {0}".format(message_list))

        # Iterate through message_list and write message
        finalIndex = self.recurseWrite(message_list, output_message, length, ASNLength, LILength, index, parameters)

        # logging.debug("Done with that list")

        # Compute lengths and edit output_message accordingly
        self.writeLengths(output_message,length,ASNLength, LILength, finalIndex) #takes in index of length and index of what length was supposed to

        return bytes(output_message)

    # Writes TextIds
    def writeTextIdLabel(self, message_list, output_message, length, ASNLength, LILength, index, parameters):

        # logging.debug('Trying to index "{0}"'.format(parameters['TextIdLabel']))
        # logging.debug('Using data keys dict: \n {0}'.format(self.DataKeys['TextId']))

        # count
        output_message += self.set16(len(parameters['TextIdLabel']))
        index += 2

        # length (stored to be calculated later)
        length['TextIdLabel_' + str(index)] = [index]
        output_message += bytearray(b'\xFF\xFF')
        index += 2

        for ids in parameters['TextIdLabel']:

            output_message += self.DataKeys['TextId'][ids]
            index += 4

        return index

    # Iterates recursively through data structure, returns index
    def recurseWrite(self,message_list,output_message, length, ASNLength, LILength, index, parameters):

        # Iterate through message list
        for data_type in message_list:

            # Check to make sure list next to "AttributeList" isn't iterated through
            if type(data_type) != list:

                # logging.debug("d: {0}".format(data_type))
                # logging.debug("p: {0}".format(parameters))
                # logging.debug("tp: {0}".format(type(parameters)))
                # logging.debug("p[d]: {0}".format(parameters.get(data_type)))

                if data_type == 'TextIdLabel':

                    index = self.writeTextIdLabel(message_list, output_message, length, ASNLength, LILength, index, parameters)

                # If data can still be broken down farther along the tree, then do so
                elif self.DataTypes.get(data_type,'none') != 'none' and type(self.DataTypes.get(data_type,'none')[0]) != int:

                    index = self.recurseWrite(self.DataTypes[data_type], output_message, length, ASNLength, LILength, index, parameters)

                # Separate method to write AttributeLists
                elif data_type == 'AttributeList':

                    index = self.writeAttributeList(message_list, output_message, length, ASNLength, LILength, index, parameters)

                # Separate method to write AttributeIdLists
                elif data_type == 'AttributeIdList':

                    index = self.writeAttributeIdList(message_list, output_message, length, ASNLength, LILength, index, parameters)

                # Store length starting index
                elif 'length' in data_type:

                    length[data_type.split("_",1)[1] + '_' + str(index)] = [index]
                    output_message += bytearray(b'\xFF\xFF')
                    index += 2

                elif 'ASNLength' in data_type:
                    ASNLength[data_type.split("_",1)[1] + '_' + str(index)] = [index]
                    output_message += bytearray(b'\xFF')
                    index += 1

                elif 'LILength' in data_type:
                    LILength[data_type.split("_",1)[1] + '_' + str(index)] = [index]
                    output_message += bytearray(b'\xFF')
                    index += 1

                # If the variable is an integer that isn't defined in DataKeys,
                # then use parameter values for the definition
                elif self.DataKeys.get(data_type, 'Not Defined') == 'Not Defined':

                    # Set value based on parameters
                    value = parameters[data_type]

                    if type(value) == list:
                        value = value[0]
                        del parameters[data_type][0]

                    # Write in value based on data_type
                    if self.DataTypes[data_type][0] == 32:
                        output_message += bytes(self.set32(value))
                        index += len(bytes(self.set32(value)))

                    elif self.DataTypes[data_type][0] == 16:
                        output_message += bytes(self.set16(value))
                        index += len(bytes(self.set16(value)))

                # if DataKeys just a bytearray, then add array to output_message
                elif type(self.DataKeys[data_type]) == bytearray:

                    output_message += self.DataKeys[data_type]
                    index += len(self.DataKeys[data_type])

                # If DataKeys dict, then use parameters to discover which
                # value to use
                elif type(self.DataKeys[data_type]) == dict:

                    keyed_value = parameters[data_type]

                    # If list, that means multiple of the same type (so can't)
                    # use dict - solution is to store the values IN ORDER
                    # in parameter list, and then delete them once they are used
                    if type(keyed_value) == list:
                        output_message += self.DataKeys[data_type][keyed_value[0]]
                        index += len(self.DataKeys[data_type][keyed_value[0]])
                        del parameters[data_type][0]

                    else:
                        output_message += self.DataKeys[data_type][keyed_value]
                        index += len(self.DataKeys[data_type][keyed_value])

                # If data type not defined print it out
                else:
                    logging.warn('Could not find data type for: ' + data_type)

                # Check end indicies of lengths
                for k in length.keys():

                    if data_type in k:

                        length[k].append(index-1)


                for k in ASNLength.keys():

                    if data_type in k:

                        ASNLength[k].append(index-1)


                for k in LILength.keys():

                    if data_type in k:

                        LILength[k].append(index-1)

        return index

    # Determines message type based on first few bytes
    def getMessageType(self, data):

        if not data:
            return

        message_type = None

        if data == b'':
            message_type = "TimeoutError"

        elif data[0:4] == b'\x00\x00\x01\x00':
            message_type = 'ConnectIndicationEvent'

        elif data[0:1] == b'\x0E':
            message_type = 'AssociationResponse'

        elif data[0:1] == b'\x0C':
            message_type = 'AssociationRefuse'

        elif data[0:1] == b'\x0A':
            message_type = 'ReleaseResponse'

        elif data[0:2] == b'\x19\x2E':
            message_type = 'AssociationAbort'

        elif data[0:1] == b'\x09':
            message_type = 'ReleaseRequest'

        elif data[0:1] == b'\xE1':

            if data[4:6] == b'\x00\x05' and data[22:24] == b'\x0C\x16':
                message_type = 'LinkedMDSSinglePollActionResult'

            elif data[4:6] == b'\x00\x05' and data[22:24] == b'\xF1\x3B':
                message_type = 'LinkedMDSExtendedPollActionResult'

            elif data[10:12] == b'\x00\x01':
                message_type = 'MDSCreateEvent'

            elif data[4:6] == b'\x00\x03':
                message_type = 'RemoteOperationError'

            elif data[20:22] == b'\x0C\x16':
                message_type = 'MDSSinglePollActionResult'

            elif data[20:22] == b'\xF1\x3B':
                message_type = 'MDSExtendedPollActionResult'

            elif data[10:12] == b'\x00\x03':
                message_type = 'MDSGetPriorityListResult'

            elif data[10:12] == b'\x00\x05':
                message_type = 'MDSSetPriorityListResult'

        else:
            message_type = 'Unknown'

        return message_type


if __name__ == '__main__':

    IntellivueDecoder()