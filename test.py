import netCDF4
import os

# 테스트할 NetCDF 파일 경로 (프로젝트 내 샘플 파일 사용)
NC_FILE = 'netcdfweb/static/ncfiles/gk2aamile1bsw038ko020lc202510171502.nc'

def print_all_meta_keys(filepath):
    """
    NetCDF 파일을 읽어서 모든 메타정보의 키를 출력하는 함수
    - Global Attributes 키 목록
    - Variables 키 목록
    - Dimensions 키 목록
    """
    print(f'파일: {os.path.basename(filepath)}')
    print('=' * 60)

    with netCDF4.Dataset(filepath, 'r') as nc:
        # 1. Global Attributes (전역 속성) 키 출력
        global_attr_keys = nc.ncattrs()
        print(f'\n[Global Attributes] 총 {len(global_attr_keys)}개')
        print('-' * 40)
        for key in global_attr_keys:
            value = getattr(nc, key)
            print(f'  {key}: {value}')

        # 2. Variables (변수) 키 출력 — 변수별 shape, dtype, 속성도 함께 출력
        variable_keys = list(nc.variables.keys())
        print(f'\n[Variables] 총 {len(variable_keys)}개')
        print('-' * 40)
        for key in variable_keys:
            var = nc.variables[key]
            # 변수의 shape, dtype, 속성 목록 출력
            attrs = {a: getattr(var, a) for a in var.ncattrs()}
            print(f'  {key}')
            print(f'    shape : {var.shape}')
            print(f'    dtype : {var.dtype}')
            for attr_key, attr_val in attrs.items():
                print(f'    {attr_key}: {attr_val}')

        # 3. Dimensions (차원) 키 출력
        dimension_keys = list(nc.dimensions.keys())
        print(f'\n[Dimensions] 총 {len(dimension_keys)}개')
        print('-' * 40)
        for key in dimension_keys:
            dim = nc.dimensions[key]
            # 차원 이름과 크기를 함께 출력
            print(f'  {key}  (size={dim.size}, unlimited={dim.isunlimited()})')

    print('\n' + '=' * 60)
    print('출력 완료')


if __name__ == '__main__':
    # 파일 존재 여부 확인 후 실행
    if not os.path.exists(NC_FILE):
        print(f'파일을 찾을 수 없습니다: {NC_FILE}')
    else:
        print_all_meta_keys(NC_FILE)
