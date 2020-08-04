#include "Entry.h"
#include "../utility/Factory.h"
#include "../utility/TypeTraits.h"
#include "../utility/fancy_print.h"
#include "DataBlock.h"
namespace sp::db
{
class EntryArrayDefault;
class EntryObjectDefault;
//-----------------------------------------------------------------------------------------------------------
Entry::Entry() {}

Entry::~Entry() {}

Entry& Entry::fetch() { return base_type::index() == type_tags::Reference ? *std::get<type_tags::Reference>(*this) : *this; }

const Entry& Entry::fetch() const { return base_type::index() == type_tags::Reference ? *std::get<type_tags::Reference>(*this) : *this; }

void Entry::update()
{
    if (base_type::index() == type_tags::Reference)
    {
        std::get<type_tags::Reference>(*this)->update();
    }
}

std::size_t Entry::type() const { return fetch().index(); }

void Entry::clear() { base_type::emplace<std::nullptr_t>(nullptr); }

DataBlock& Entry::as_block()
{
    switch (base_type::index())
    {
    case type_tags::Empty:
        emplace<type_tags::Block>(std::make_shared<DataBlock>());
        break;
    case type_tags::Block:
        break;
    case type_tags::Reference:
        std::get<type_tags::Reference>(*this)->as_block();
        break;
    default:
        throw std::runtime_error("illegal type");
        break;
    }
    return *std::get<type_tags::Block>(fetch());
}

const DataBlock& Entry::as_block() const
{

    if (type() != type_tags::Block)
    {
        throw std::runtime_error("illegal type");
    }
    return *std::get<type_tags::Block>(fetch());
}

EntryObject& Entry::as_object()
{
    switch (base_type::index())
    {
    case type_tags::Empty:
        emplace<type_tags::Object>(EntryObject::create(this));
        break;
    case type_tags::Object:
        break;
    case type_tags::Reference:
        std::get<type_tags::Reference>(*this)->as_object();
        break;
    default:
        throw std::runtime_error("illegal type");
        break;
    }
    return *std::get<type_tags::Object>(fetch());
}

const EntryObject& Entry::as_object() const
{
    if (type() != type_tags::Object)
    {
        throw std::runtime_error("illegal type");
    }
    return *std::get<type_tags::Object>(fetch());
}

EntryArray& Entry::as_array()
{
    switch (base_type::index())
    {
    case type_tags::Empty:
        emplace<type_tags::Array>(EntryArray::create(this));
        break;
    case type_tags::Array:
        break;

    case type_tags::Reference:
        std::get<type_tags::Reference>(*this)->as_array();
        update();
        break;
    default:
        throw std::runtime_error("illegal type");
        break;
    }
    return *std::get<type_tags::Array>(fetch());
}

const EntryArray& Entry::as_array() const
{
    if (index() != type_tags::Array)
    {
        throw std::runtime_error("illegal type");
    }
    return *std::get<type_tags::Array>(fetch());
}

// Entry& Entry::insert(const std::string& path) { return as_object().insert(path); }
// Entry& Entry::insert(int idx) { return as_array().at(idx); }

// const Entry& Entry::at(const std::string& path) const { return as_object().at(path); }
// const Entry& Entry::at(int idx) const { return as_array().at(idx); }

//-----------------------------------------------------------------------------------------------------------
EntryObject::EntryObject(Entry* s) : m_self_(s) {}

EntryObject::~EntryObject() {}

std::shared_ptr<EntryObject> EntryObject::create(Entry* self, const std::string& request)
{
    if (request == "")
    {
        return std::dynamic_pointer_cast<EntryObject>(std::make_shared<EntryObjectDefault>(self));
    }

    std::string schema = "";

    auto pos = request.find(":");

    if (pos == std::string::npos)
    {
        pos = request.rfind('.');
        if (pos != std::string::npos)
        {
            schema = request.substr(pos);
        }
        else
        {
            schema = request;
        }
    }
    else
    {
        schema = request.substr(0, pos);
    }

    if (schema == "http" || schema == "https")
    {
        NOT_IMPLEMENTED;
    }

    std::shared_ptr<EntryObject> obj;

    if (schema == "")
    {
        obj = std::dynamic_pointer_cast<EntryObject>(std::make_shared<EntryObjectDefault>(self));
    }
    else if (Factory<EntryObject>::has_creator(schema))
    {
        obj = std::shared_ptr<EntryObject>(Factory<EntryObject>::create(schema).release());
    }
    else
    {
        RUNTIME_ERROR << "Can not parse schema " << schema << std::endl;
    }

    if (obj == nullptr)
    {
        throw std::runtime_error("Can not create Entry for schema: " + schema);
    }
    else
    {
        VERBOSE << "load backend:" << schema << std::endl;
    }

    // if (schema != request)
    // {
    //     res->fetch(request);
    // }
    obj->self(self);
    return obj;
}

bool EntryObject::add_creator(const std::string& c_id, const std::function<EntryObject*()>& fun)
{
    return Factory<EntryObject>::add(c_id, fun);
};

Entry& EntryObject::insert(const XPath& path)
{

    Entry* p = m_self_;
    for (auto it = path.begin(); it != path.end(); ++it)
    {
        switch (it->index())
        {
        case XPath::type_tags::Key:
            p = &p->as_object().insert(std::get<XPath::type_tags::Key>(*it));
            break;
        case XPath::type_tags::Index:
            p = &p->as_array().at(std::get<XPath::type_tags::Index>(*it));
            break;
        default:
            NOT_IMPLEMENTED;
            break;
        }
    }
    return *p;
}

const Entry& EntryObject::at(const XPath& path) const
{

    const Entry* p = m_self_;
    for (auto it = path.begin(); it != path.end(); ++it)
    {
        switch (it->index())
        {
        case XPath::type_tags::Key:
            p = &p->as_object().at(std::get<XPath::type_tags::Key>(*it));
            break;
        case XPath::type_tags::Index:
            p = &p->as_array().at(std::get<XPath::type_tags::Index>(*it));
            break;
        default:
            NOT_IMPLEMENTED;
            break;
        }
    }
    return *p;
    ;
}

void EntryObject::erase(const XPath& path) { NOT_IMPLEMENTED; }

Cursor<Entry> EntryObject::select(const XPath& path) { NOT_IMPLEMENTED; }

Cursor<const Entry> EntryObject::select(const XPath& path) const { NOT_IMPLEMENTED; }
//-----------------------------------------------------------------------------------------------------------
EntryArray::EntryArray(Entry* s) : m_self_(s) {}

EntryArray::~EntryArray() {}

std::shared_ptr<EntryArray> EntryArray::create(Entry* self, const std::string& request)
{
    auto res = std::dynamic_pointer_cast<EntryArray>(std::make_shared<EntryArrayDefault>(self));
    res->self(self);
    return res;
};

//-----------------------------------------------------------------------------------------------------------

class EntryObjectDefault : public EntryObject
{
public:
    typedef EntryObjectDefault this_type;
    typedef Entry::type_tags type_tags;

    EntryObjectDefault(Entry* self) : EntryObject(self) {}

    EntryObjectDefault(const this_type& other) : EntryObject(nullptr), m_container_(other.m_container_) {}

    EntryObjectDefault(EntryObjectDefault&& other) : EntryObject(nullptr), m_container_(std::move(other.m_container_)) {}

    ~EntryObjectDefault() = default;

    std::shared_ptr<EntryObject> copy() const override { return std::shared_ptr<EntryObject>(new this_type(*this)); }

    //----------------------------------------------------------------------------------------------------------

    //----------------------------------------------------------------------------------------------------------
    // as leaf node,  need node.type = Scalar || Block
    //----------------------------------------------------------------------------------------------------------
    //----------------------------------------------------------------------------------------------------------
    // as Hierarchy tree node
    // function level 0

    size_t size() const override { return m_container_.size(); }

    void clear() override { m_container_.clear(); }

    // as object

    Entry& insert(const std::string& path) override;

    // Entry& insert(const XPath& path) override;

    const Entry& at(const std::string& path) const override;

    // const Entry& at(const XPath& path) const override;

    void erase(const std::string& path) override;

    // void erase(const XPath& path) override;

    //------------------------------------------------------------------

    // Cursor<Entry> select(const XPath& path) override;

    // Cursor<const Entry> select(const XPath& path) const override;

    Cursor<Entry> children() override;

    Cursor<const Entry> children() const override;

    Cursor<std::pair<const std::string, Entry>> kv_items() override;

    Cursor<std::pair<const std::string, Entry>> kv_items() const override;

private:
    std::map<std::string, Entry> m_container_;
};

Entry&
EntryObjectDefault::insert(const std::string& name) { return m_container_.try_emplace(name).first->second; }

const Entry&
EntryObjectDefault::at(const std::string& path) const { return m_container_.at(path); }

void EntryObjectDefault::erase(const std::string& path) {  m_container_.erase(m_container_.find(path)); }

//--------------------------------------------------------------------------------------------------------------------------------------------

Cursor<Entry>
EntryObjectDefault::children() { return make_cursor(m_container_.begin(), m_container_.end()).map<Entry>(); }

Cursor<const Entry>
EntryObjectDefault::children() const { return make_cursor(m_container_.cbegin(), m_container_.cend()).map<const Entry>(); }

Cursor<std::pair<const std::string, Entry>> EntryObjectDefault::kv_items() { return make_cursor(m_container_.begin(), m_container_.end()); };

Cursor<std::pair<const std::string, Entry>> EntryObjectDefault::kv_items() const { return make_cursor(m_container_.cbegin(), m_container_.cend()); };

//--------------------------------------------------------------------------------

class EntryArrayDefault : public EntryArray
{
public:
    typedef Entry::type_tags type_tags;
    typedef EntryArrayDefault this_type;

    EntryArrayDefault(Entry* self) : EntryArray(self) {}

    ~EntryArrayDefault() = default;

    EntryArrayDefault(const this_type& other) : EntryArray(nullptr), m_container_(other.m_container_) {}

    EntryArrayDefault(EntryArrayDefault&& other) : EntryArray(nullptr), m_container_(std::move(other.m_container_)) {}

    // as array

    std::shared_ptr<EntryArray> copy() const override { return std::dynamic_pointer_cast<EntryArray>(std::make_shared<EntryArrayDefault>(*this)); }

    size_t size() const override { return m_container_.size(); }

    void clear() override { m_container_.clear(); }

    void resize(std::size_t num) override;

    Entry& push_back() override;

    void pop_back() override;

    Cursor<Entry> item(int idx) override;

    Cursor<const Entry> item(int idx) const override;

    Entry& at(int idx) override;

    const Entry& at(int idx) const override;

    Cursor<Entry> children();

    Cursor<const Entry> children() const;

private:
    std::vector<Entry> m_container_;
};

void EntryArrayDefault::resize(std::size_t num) { m_container_.resize(num); }

Cursor<Entry> EntryArrayDefault::children() { return make_cursor(m_container_.begin(), m_container_.end()); }

Cursor<const Entry> EntryArrayDefault::children() const { return make_cursor(m_container_.begin(), m_container_.end()).map<const Entry>(); }

Entry& EntryArrayDefault::push_back() { return m_container_.emplace_back(); }

void EntryArrayDefault::pop_back() { m_container_.pop_back(); }

const Entry& EntryArrayDefault::at(int idx) const { return m_container_.at(idx); }

Entry& EntryArrayDefault::at(int idx) { return m_container_.at(idx); }

Cursor<const Entry> EntryArrayDefault::item(int idx) const { return make_cursor(&m_container_.at(idx)); }

Cursor<Entry> EntryArrayDefault::item(int idx) { return make_cursor(&m_container_.at(idx)); }

} // namespace sp::db
namespace sp::utility
{
std::ostream& fancy_print(std::ostream& os, const sp::db::Entry& entry, int indent = 0, int tab = 4)
{
    std::visit(sp::traits::overloaded{
                   [&](const std::variant_alternative_t<sp::db::Entry::type_tags::Array, sp::db::Entry::base_type>& ele) {
                       os << "[";
                       for (auto it = ele->children(); !it.done(); it.next())
                       {
                           os << std::endl
                              << std::setw(indent * tab) << " ";
                           fancy_print(os, *it, indent + 1, tab);
                           os << ",";
                       }
                       os << std::endl
                          << std::setw(indent * tab)
                          << "]";
                   },
                   [&](const std::variant_alternative_t<sp::db::Entry::type_tags::Object, sp::db::Entry::base_type>& ele) {
                       os << "{";
                       for (auto it = ele->kv_items(); !it.done(); it.next())
                       {
                           os << std::endl
                              << std::setw(indent * tab) << " "
                              << "\"" << it->first << "\" : ";
                           fancy_print(os, it->second, indent + 1, tab);
                           os << ",";
                       }
                       os << std::endl
                          << std::setw(indent * tab)
                          << "}";
                   },
                   [&](const std::variant_alternative_t<sp::db::Entry::type_tags::Empty, sp::db::Entry::base_type>& ele) { fancy_print(os, nullptr, indent + 1, tab); },
                   [&](auto&& ele) { fancy_print(os, ele, indent + 1, tab); } //
               },
               dynamic_cast<const sp::db::Entry::base_type&>(entry));

    // if (entry.type() == Entry::NodeType::Element)
    // {
    //     os << to_string(entry.get_element());
    // }
    // else if (entry.type() == Entry::NodeType::Array)
    // else if (entry.type() == Entry::NodeType::Object)
    // {
    //
    // }
    return os;
}
} // namespace sp::utility
namespace sp::db
{
std::ostream& operator<<(std::ostream& os, Entry const& entry) { return sp::utility::fancy_print(os, entry, 0); }
} // namespace sp::db