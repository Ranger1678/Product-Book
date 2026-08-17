import sqlite3
import os
import pandas as pd
import streamlit as st
import time

# 配置页面宽度和标题
st.set_page_config(page_title="SKU查询系统", layout="wide")
st.title("SKU查询系统")

DB_FILE = "master_inventory.db"
TABLE_NAME = "products"

# 定义搜索字段映射
SEARCH_FIELDS = {
    "SKU": "传统编码",
    "英文描述": "产品英文描述",  
    "车型年份": "类目三",
    "OE": "OE No."
}

# 数据库查询函数 - 支持分页
def query_data(search_term="", search_field="传统编码", offset=0, limit=100):
    conn = sqlite3.connect(DB_FILE)
    
    # 验证搜索字段是否合法
    valid_fields = list(SEARCH_FIELDS.values())
    if search_field not in valid_fields:
        search_field = "传统编码"
    
    if search_term:
        query = f'SELECT * FROM {TABLE_NAME} WHERE {search_field} LIKE ? LIMIT ? OFFSET ?'
        df = pd.read_sql_query(query, conn, params=(f'%{search_term}%', limit, offset))
    else:
        query = f'SELECT * FROM {TABLE_NAME} LIMIT ? OFFSET ?'
        df = pd.read_sql_query(query, conn, params=(limit, offset))
    
    conn.close()
    return df

# 获取总记录数
def get_total_count(search_term="", search_field="传统编码"):
    conn = sqlite3.connect(DB_FILE)
    valid_fields = list(SEARCH_FIELDS.values())
    if search_field not in valid_fields:
        search_field = "传统编码"
    
    if search_term:
        query = f'SELECT COUNT(*) FROM {TABLE_NAME} WHERE {search_field} LIKE ?'
        cursor = conn.cursor()
        cursor.execute(query, (f'%{search_term}%',))
    else:
        query = f'SELECT COUNT(*) FROM {TABLE_NAME}'
        cursor = conn.cursor()
        cursor.execute(query)
    
    count = cursor.fetchone()[0]
    conn.close()
    return count

# 初始化session state
if 'offset' not in st.session_state:
    st.session_state.offset = 0
if 'all_data' not in st.session_state:
    st.session_state.all_data = pd.DataFrame()
if 'has_more' not in st.session_state:
    st.session_state.has_more = True
if 'search_term' not in st.session_state:
    st.session_state.search_term = ""
if 'search_field' not in st.session_state:
    st.session_state.search_field = "传统编码"
if 'total_count' not in st.session_state:
    st.session_state.total_count = 0
if 'load_trigger' not in st.session_state:
    st.session_state.load_trigger = 0

# 重置数据函数
def reset_data():
    st.session_state.offset = 0
    st.session_state.all_data = pd.DataFrame()
    st.session_state.has_more = True
    st.session_state.load_trigger = 0

# 加载更多数据
def load_more():
    if st.session_state.has_more:
        new_data = query_data(
            st.session_state.search_term, 
            st.session_state.search_field, 
            st.session_state.offset, 
            100
        )
        
        if not new_data.empty:
            st.session_state.all_data = pd.concat([st.session_state.all_data, new_data], ignore_index=True)
            st.session_state.offset += 100
            
            if len(st.session_state.all_data) >= st.session_state.total_count:
                st.session_state.has_more = False
        else:
            st.session_state.has_more = False

# 美化数据显示函数 - 无滚动条版本
def display_data_table(row):
    """以表格形式显示单条数据，无滚动条"""
    filter_fields = ['image_path', '助记码', '所属类别', '新品', '停用', '外购', '自制']
    
    # 构建显示数据
    display_data = []
    for k, v in row.items():
        if k not in filter_fields and pd.notna(v):
            # 限制显示长度，避免过长
            value_str = str(v)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            display_data.append({"字段": k, "值": value_str})
    
    # 创建DataFrame
    df_display = pd.DataFrame(display_data)
    
    # 不设置高度限制，完全展开显示
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "字段": st.column_config.TextColumn("字段名", width="small"),
            "值": st.column_config.TextColumn("内容", width="large")
        }
    )

# 创建搜索区域
st.markdown("### 🔍 搜索条件")
col1, col2 = st.columns([1, 3])

with col1:
    search_type = st.selectbox(
        "选择搜索方式",
        options=list(SEARCH_FIELDS.keys()),
        help="选择要按哪个字段进行搜索",
        key="search_type_select"
    )

with col2:
    search_sku = st.text_input(
        f"输入 {search_type} 搜索（留空默认显示前30条数据）：",
        placeholder=f"请输入要搜索的{search_type}...",
        key="search_input"
    )

# 获取对应的数据库字段名
search_field = SEARCH_FIELDS[search_type]

# 检测搜索条件是否变化
current_search_key = f"{search_sku}_{search_field}"
if 'last_search_key' not in st.session_state or st.session_state.last_search_key != current_search_key:
    st.session_state.search_term = search_sku
    st.session_state.search_field = search_field
    st.session_state.last_search_key = current_search_key
    reset_data()
    st.session_state.total_count = get_total_count(search_sku, search_field)

# 首次加载或数据为空时加载
if st.session_state.all_data.empty and st.session_state.has_more:
    initial_data = query_data(
        st.session_state.search_term, 
        st.session_state.search_field, 
        0, 
        100
    )
    st.session_state.all_data = initial_data
    st.session_state.offset = 100
    
    if len(st.session_state.all_data) >= st.session_state.total_count:
        st.session_state.has_more = False

# 显示结果
df_results = st.session_state.all_data

if df_results.empty:
    st.warning("未找到匹配的数据！")
else:
    st.success(f"✅ 共找到 **{st.session_state.total_count}** 条记录（按 **{search_type}** 搜索），已加载 **{len(df_results)}** 条")
    
    # 创建显示容器
    main_container = st.container()
    
    with main_container:
        # 逐行渲染产品信息与图片
        for idx, row in df_results.iterrows():
            with st.container():
                # 调整列比例为 1:2.5
                col_img, col_info = st.columns([1, 2.5])
                
                # 左侧：显示图片（无滚动条）
                img_path = str(row.get('image_path', ''))
                with col_img:
                    if img_path and os.path.exists(img_path):
                        # 直接显示图片，不限制高度
                        st.image(img_path, use_container_width=True, caption=f"传统编码: {row.get('传统编码', '')}")
                    else:
                        # 显示占位信息
                        st.markdown(
                            """
                            <div style="display: flex; justify-content: center; align-items: center; height: 200px; background-color: #f0f2f6; border-radius: 10px;">
                                <span style="color: #666; font-size: 18px;">📷 暂无图片</span>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                
                # 右侧：以表格形式显示文本信息（无滚动条）
                with col_info:
                    # 显示匹配字段高亮
                    st.markdown(f"**🔖 搜索匹配:** `{search_type} = {row.get(search_field, 'N/A')}`")
                    
                    # 以表格形式显示数据（无高度限制）
                    display_data_table(row)
                    
                st.divider()
        
        # 在列表底部显示加载状态和自动加载
        if st.session_state.has_more:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.info(f"📥 已加载 {len(df_results)} 条，共 {st.session_state.total_count} 条")
                
                # 自动加载按钮
                load_button = st.button("加载更多 (自动)", key="auto_load_btn", use_container_width=True)
                
                # JavaScript监听滚动
                st.markdown("""
                <div id="bottom-trigger" style="height: 10px;"></div>
                <script>
                    const observer = new IntersectionObserver((entries) => {
                        entries.forEach(entry => {
                            if (entry.isIntersecting) {
                                const buttons = document.querySelectorAll('button');
                                for (let btn of buttons) {
                                    if (btn.textContent.includes('加载更多')) {
                                        btn.click();
                                        break;
                                    }
                                }
                            }
                        });
                    }, {
                        root: null,
                        rootMargin: '0px 0px 50px 0px',
                        threshold: 0.1
                    });
                    
                    function setupObserver() {
                        const trigger = document.getElementById('bottom-trigger');
                        if (trigger) {
                            observer.observe(trigger);
                        } else {
                            setTimeout(setupObserver, 100);
                        }
                    }
                    setupObserver();
                </script>
                """, unsafe_allow_html=True)
                
                if load_button:
                    load_more()
                    st.rerun()
        else:
            if st.session_state.total_count > 0:
                st.success(f"✅ 已加载全部 {len(df_results)} 条数据")