import struct
import uuid
import hashlib
import zlib
import logging
import traceback
from typing import Dict, Set, List, Optional, Any, Union

from .constants import *
from .windows_time import WindowsTime
from .validators import validate_attribute_length, ValidationError


class MftRecord:
    
    def __init__(self, raw_record: bytes, compute_hashes: bool = False, debug_level: int = 0, logger=None):
        
        if len(raw_record) < MFT_RECORD_SIZE:
            raise ValueError(f"MFT record too short: {len(raw_record)} bytes, expected {MFT_RECORD_SIZE}")

        self.raw_record = raw_record
        self.debug_level = debug_level
        self.logger = logger or logging.getLogger('analyzeMFT.mft_record')
        
        self.magic = 0
        self.upd_off = 0
        self.upd_cnt = 0
        self.lsn = 0
        self.seq = 0
        self.link = 0
        self.attr_off = 0
        self.flags = 0
        self.size = 0
        self.alloc_sizef = 0
        self.base_ref = 0
        self.next_attrid = 0
        self.recordnum = 0
        self.filename = ''
        self.parent_ref = 0
        self.filesize = 0
        
        self.si_times = {
            'crtime': WindowsTime(0, 0),
            'mtime': WindowsTime(0, 0),
            'atime': WindowsTime(0, 0),
            'ctime': WindowsTime(0, 0)
        }
        self.fn_times = {
            'crtime': WindowsTime(0, 0),
            'mtime': WindowsTime(0, 0),
            'atime': WindowsTime(0, 0),
            'ctime': WindowsTime(0, 0)
        }
        self.attribute_types: Set[int] = set()
        self.attribute_list: List[Dict] = []
        self.object_id = ''
        self.birth_volume_id = ''
        self.birth_object_id = ''
        self.birth_domain_id = ''

        self.security_descriptor: Optional[Dict] = None
        self.volume_name: Optional[str] = None
        self.volume_info: Optional[Dict] = None
        self.data_attribute: Optional[Dict] = None
        self.index_root: Optional[Dict] = None
        self.index_allocation: Optional[Dict] = None
        self.bitmap: Optional[Dict] = None
        self.reparse_point: Optional[Dict] = None
        self.ea_information: Optional[Dict] = None
        self.ea: Optional[Dict] = None
        self.logged_utility_stream: Optional[Dict] = None
        self.md5: Optional[str] = None
        self.sha256: Optional[str] = None
        self.sha512: Optional[str] = None
        self.crc32: Optional[str] = None
        
        if compute_hashes:
            self.compute_hashes()
        self.parse_record()

    def log(self, message: str, level: int = 0) -> None:

        pass

    def parse_record(self) -> None:
        pass

    def parse_attributes(self) -> None:
        pass

    def parse_si_attribute(self, offset: int) -> None:
        pass

    def parse_fn_attribute(self, offset: int) -> None:
        pass

    def parse_object_id_attribute(self, offset: int) -> None:
        pass
    
    def get_parent_record_num(self) -> int:
        return self.parent_ref & 0x0000FFFFFFFFFFFF

    def parse_attribute_list(self, offset: int) -> None:
        pass

    def parse_security_descriptor(self, offset: int) -> None:
        pass

    def parse_volume_name(self, offset: int) -> None:
        pass

    def parse_volume_information(self, offset: int) -> None:
        pass

    def parse_data(self, offset: int) -> None:
        pass

    def parse_index_root(self, offset: int) -> None:
        pass

    def parse_index_allocation(self, offset: int) -> None:
        pass

    def parse_bitmap(self, offset: int) -> None:
        pass

    def parse_reparse_point(self, offset: int) -> None:
        pass

    def parse_ea_information(self, offset: int) -> None:
        pass

    def parse_ea(self, offset: int) -> None:
        pass

    def parse_logged_utility_stream(self, offset: int) -> None:
        pass

    def to_csv(self) -> List[Union[str, int]]:
        row = [
            self.recordnum,
            "Valid" if self.magic == int.from_bytes(MFT_RECORD_MAGIC, BYTE_ORDER) else "Invalid",
            "In Use" if self.flags & FILE_RECORD_IN_USE else "Not in Use",
            self.get_file_type(),
            self.seq,
            self.get_parent_record_num(),
            self.base_ref >> 48,
            
            self.filename, "",  
            
            self.si_times['crtime'].dtstr,
            self.si_times['mtime'].dtstr,
            self.si_times['atime'].dtstr,
            self.si_times['ctime'].dtstr,
            
            self.fn_times['crtime'].dtstr,
            self.fn_times['mtime'].dtstr,
            self.fn_times['atime'].dtstr,
            self.fn_times['ctime'].dtstr,
            
            self.object_id,
            self.birth_volume_id,
            self.birth_object_id,
            self.birth_domain_id,
            
            str(STANDARD_INFORMATION_ATTRIBUTE in self.attribute_types),
            str(ATTRIBUTE_LIST_ATTRIBUTE in self.attribute_types),
            str(FILE_NAME_ATTRIBUTE in self.attribute_types),
            str(VOLUME_NAME_ATTRIBUTE in self.attribute_types),
            str(VOLUME_INFORMATION_ATTRIBUTE in self.attribute_types),
            str(DATA_ATTRIBUTE in self.attribute_types),
            str(INDEX_ROOT_ATTRIBUTE in self.attribute_types),
            str(INDEX_ALLOCATION_ATTRIBUTE in self.attribute_types),
            str(BITMAP_ATTRIBUTE in self.attribute_types),
            str(REPARSE_POINT_ATTRIBUTE in self.attribute_types),
            str(EA_INFORMATION_ATTRIBUTE in self.attribute_types),
            str(EA_ATTRIBUTE in self.attribute_types),
            str(LOGGED_UTILITY_STREAM_ATTRIBUTE in self.attribute_types),
            
            str(self.attribute_list),
            str(self.security_descriptor),
            self.volume_name or "",
            str(self.volume_info),
            str(self.data_attribute),
            str(self.index_root),
            str(self.index_allocation),
            str(self.bitmap),
            str(self.reparse_point),
            str(self.ea_information),
            str(self.ea),
            str(self.logged_utility_stream)
        ]
        
        if self.md5 is not None:
            row.extend([self.md5, self.sha256, self.sha512, self.crc32])
        else:
            row.extend([""] * 4)
            
        return row

    def compute_hashes(self) -> None:

        pass

    def set_hashes(self, md5: str, sha256: str, sha512: str, crc32: str) -> None:

        self.md5 = md5
        self.sha256 = sha256
        self.sha512 = sha512
        self.crc32 = crc32

    def get_file_type(self) -> str:
        if self.flags & FILE_RECORD_IS_DIRECTORY:
            return "Directory"
        elif self.flags & FILE_RECORD_IS_EXTENSION:
            return "Extension"
        elif self.flags & FILE_RECORD_HAS_SPECIAL_INDEX:
            return "Special Index"
        else:
            return "File"
    
    def parse_object_id(self, offset: int) -> None:
        pass
