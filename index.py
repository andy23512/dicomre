import numpy as np
import os
import pydicom
import sys
from tqdm import tqdm

REMOVED_FIELDS = [
    'PatientName',                      # (0010,0010)
    'OtherPatientNames',                # (0010,1001)
    'PatientBirthName',                 # (0010,1005)
    'PatientMotherBirthName',           # (0010,1060)
    'ResponsiblePerson',                # (0010,2297)
    'ReferringPhysicianName',           # (0008,0090)
    'PerformingPhysicianName',          # (0008,1050)
    'OperatorsName',                    # (0008,1070)
    'OtherPatientIDs',                  # (0010,1000)
    'OtherPatientIDsSequence',          # (0010,1002)
    'PatientBirthDate',                 # (0010,0030)
    'PatientBirthTime',                 # (0010,0032)
    'EthnicGroup',                      # (0010,2160)
    'PatientBreedCodeSequence',         # (0010,2293)
    'BreedRegistrationSequence',        # (0010,2294)
    'BreedRegistrationNumber',          # (0010,2295)
    'BreedRegistryCodeSequence',        # (0010,2296)
    'PatientSpeciesCodeSequence',       # (0010,2202)
    'MilitaryRank',                     # (0010,1080)
    'BranchOfService',                  # (0010,1081)
    'Occupation',                       # (0010,2180)
    'PatientID',                        # (0010,0020)
    'IssuerOfPatientID',                # (0010,0021)
    'TypeOfPatientID',                  # (0010,0022)
    'MedicalRecordLocator',             # (0010,1090)
    'AdditionalPatientHistory',         # (0010,21B0)
    'LastMenstrualDate',                # (0010,21D0)
    'PatientSexNeutered',               # (0010,2203)
    'PregnancyStatus',                  # (0010,21C0)
    'PatientAddress',                   # (0010,1040)
    'CountryOfResidence',               # (0010,2150)
    'RegionOfResidence',                # (0010,2152)
    'PatientTelephoneNumbers',          # (0010,2154)
    'PatientInsurancePlanCodeSequence', # (0010,0050)
    'InsurancePlanIdentification',      # (0010,1050)
    'PatientPrimaryLanguageCodeSeq',    # (0010,0101)
    'PatientPrimaryLanguageCodeModSeq', # (0010,0102)
    'PatientReligiousPreference',       # (0010,21F0)
    'ResponsiblePersonRole',            # (0010,2298)
    'ResponsibleOrganization',          # (0010,2299)
    'AccessionNumber',                  # (0008,0050)
    'InstitutionName',                  # (0008,0080)
]


def generate_stripe(narray, i):
    a = np.zeros(narray.shape, dtype=np.int16)
    for y in range(narray.shape[0]):
        if i % 2 == 0:
            if y % 10 < 5:
                value = -2048
            else:
                value = 0
        else:
            value = -1024
        for x in range(narray.shape[1]):
            a[y][x] = value
    return a


class LoadSeriesFolder():
    def __init__(self, series_folder):
        self.path = series_folder['path']
        self.dicom_files = series_folder['dicom_files']
        self.series_dict = {}
        self.seriess = []

        self._get_series_dict()
        self._process_series_dict()

    def _get_series_dict(self):
        for dicom_file in self.dicom_files:
            dicom_file_path = os.path.join(self.path, dicom_file)
            dicom = pydicom.read_file(dicom_file_path)
            if dicom.SeriesInstanceUID not in self.series_dict:
                d = {'slice_indexes': [], 'dicoms': {}, 'paths': {}}
                self.series_dict[dicom.SeriesInstanceUID] = d
            else:
                d = self.series_dict[dicom.SeriesInstanceUID]
            if dicom.InstanceNumber:
                d['slice_indexes'].append(int(dicom.InstanceNumber))
                d['dicoms'][str(dicom.InstanceNumber)] = dicom
                d['paths'][str(dicom.InstanceNumber)] = dicom_file_path

    def _process_series_dict(self):
        for series_uid, series_info in self.series_dict.items():
            series_data = []
            slice_indexes = series_info['slice_indexes']
            if len(slice_indexes) > 0:
                slice_indexes.sort()
                start_index = slice_indexes[0]
                end_index = slice_indexes[-1]
                count = end_index - start_index + 1
            for i in range(start_index, start_index + count):
                path = series_info['paths'][str(i)]
                dcm = pydicom.read_file(path)
                pixel_array = generate_stripe(dcm.pixel_array, i)
                for field in REMOVED_FIELDS:
                    if hasattr(dcm, field):
                        delattr(dcm, field)
                dcm.remove_private_tags()
                dcm.PixelData = pixel_array.tobytes()
                dcm.save_as(f'./t/tmp{i}')


class LoadFolder():
    def __init__(self, root_folder):
        self.root_folder = root_folder
        self.seriess = []
        self.series_folders = []
        self._scan_series_folders()
        self._process_series_folders()

    def _scan_series_folders(self):
        for root, dirs, files in os.walk(self.root_folder):
            dirs[:] = [d for d in dirs if not d[0] == '.']
            dicom_files = list(filter(lambda f: not f.startswith('.') and not f.endswith('.lnk') and not f.endswith('.xlsx') and not f.endswith('.csv') and not f.endswith('.zip') and not f.endswith('.xml') and not f.endswith('.ini') and not f.endswith('.stl') and f not in ['DIRFILE', 'DICOMDIR', 'dirty', '_DS_Store'], files))
            self.series_folders.append({'path': root, 'dicom_files': dicom_files})

    def _process_series_folders(self):
        for index, series_folder in tqdm(enumerate(self.series_folders), desc='series_folder'):
            loaded_series_folder = LoadSeriesFolder(series_folder)
            self.seriess.extend(loaded_series_folder.seriess)


if len(sys.argv) == 1:
    print('Usage: python index.py [dicom_folder]')
    exit()
path = sys.argv[1]
if not os.path.isdir(path):
    print('Path is not a directory.')
    exit()
LoadFolder(path)
