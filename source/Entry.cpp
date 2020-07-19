#include "Entry.h"
#include "EntryInterface.h"
#include "utility/Logger.h"
#include <any>
#include <map>
#include <vector>
namespace sp
{
struct type_desc
{
};

class EntryInterfaceInMemory : public EntryInterface
{
private:
    Entry* m_self_;
    Entry* m_parent_;

    std::variant<nullptr_t,
                 Entry::single_t,
                 Entry::tensor_t,
                 Entry::block_t,
                 std::vector<Entry>,
                 std::map<std::string, Entry>>
        m_data_;

public:
    EntryInterfaceInMemory(Entry* self, Entry* parent = nullptr) : m_self_(self), m_parent_(parent), m_data_(nullptr){};

    EntryInterfaceInMemory(const EntryInterfaceInMemory& other) : m_self_(other.m_self_), m_parent_(other.m_parent_), m_data_(other.m_data_) {}

    EntryInterfaceInMemory(EntryInterfaceInMemory&& other) : m_self_(other.m_self_), m_parent_(other.m_parent_), m_data_(std::move(other.m_data_)) {}

    ~EntryInterfaceInMemory() = default;

    EntryInterface* copy() const override { return new EntryInterfaceInMemory(*this); }

    //

    std::string prefix() const
    {
        NOT_IMPLEMENTED;
        return "";
    }

    Entry::Type type() const { return Entry::Type(m_data_.index()); }

    // attributes

    bool has_attribute(const std::string& name) const { return !find("@" + name); }

    Entry::single_t get_attribute_raw(const std::string& name) const
    {
        auto p = find("@" + name);
        if (!p)
        {
            throw std::out_of_range("Can not find attribute '" + name + "'");
        }
        return p->get_single();
    }

    void set_attribute_raw(const std::string& name, const Entry::single_t& value) { insert("@" + name)->set_single(value); }

    void remove_attribute(const std::string& name) { erase("@" + name); }

    std::map<std::string, Entry::single_t> attributes() const
    {
        if (type() != Entry::Type::Object)
        {
            return std::map<std::string, Entry::single_t>{};
        }

        std::map<std::string, Entry::single_t> res;
        for (const auto& item : std::get<Entry::Type::Object>(m_data_))
        {
            if (item.first[0] == '@')
            {
                res.emplace(item.first.substr(1, std::string::npos), item.second.get_single());
            }
        }
        return std::move(res);
    }

    //----------------------------------------------------------------------------------
    // level 0
    //
    // as leaf

    void set_single(const Entry::single_t& v) override
    {
        if (type() < Entry::Type::Array)
        {
            m_data_.emplace<Entry::Type::Single>(v);
        }
        else
        {
            throw std::runtime_error("Set value failed!");
        }
    }

    Entry::single_t get_single() const override
    {
        if (type() != Entry::Type::Single)
        {
            throw std::runtime_error("This is not block!");
        }
        return std::get<Entry::Type::Single>(m_data_);
    }

    void set_tensor(const Entry::tensor_t& v) override
    {
        if (type() < Entry::Type::Array)
        {
            m_data_.emplace<Entry::Type::Tensor>(v);
        }
        else
        {
            throw std::runtime_error("Set value failed!");
        }
    }

    Entry::tensor_t get_tensor() const override
    {
        if (type() != Entry::Type::Tensor)
        {
            throw std::runtime_error("This is not block!");
        }
        return std::get<Entry::Type::Tensor>(m_data_);
    }

    void set_block(const Entry::block_t& v) override
    {
        if (type() < Entry::Type::Array)
        {
            m_data_.emplace<Entry::Type::Block>(v);
        }
        else
        {
            throw std::runtime_error("Set value failed!");
        }
    }

    Entry::block_t get_block() const override
    {
        if (type() != Entry::Type::Block)
        {
            throw std::runtime_error("This is not block!");
        }
        return std::get<Entry::Type::Block>(m_data_);
    }

    // as Tree

    Entry::iterator parent() const override { return Entry::iterator(const_cast<Entry*>(m_parent_)); }

    Entry::iterator next() const override
    {
        NOT_IMPLEMENTED;
        return Entry::iterator();
    };

    Entry::iterator first_child() override
    {
        if (type() == Entry::Type::Array)
        {
            return Entry::iterator(std::get<Entry::Type::Array>(m_data_).begin());
        }
        else if (type() == Entry::Type::Object)
        {
            return Entry::iterator(std::get<Entry::Type::Object>(m_data_).begin(),
                                   [](auto const& item) -> Entry* { return &item->second; });
        }
        return Entry::iterator();
    };

    Entry::iterator last_child() override
    {

        if (type() == Entry::Type::Array)
        {
            return Entry::iterator(std::get<Entry::Type::Array>(m_data_).end());
        }
        else if (type() == Entry::Type::Object)
        {
            return Entry::iterator(std::get<Entry::Type::Object>(m_data_).end(),
                                   [](auto const& item) -> Entry* { return &item->second; });
        }
        return Entry::iterator();
    };

    size_t size() const
    {
        NOT_IMPLEMENTED;
        return 0;
    }

    Entry::range find(const Entry::pred_fun& pred)
    {
        NOT_IMPLEMENTED;
    }

    void erase(const Entry::iterator& p)
    {
        NOT_IMPLEMENTED;
    }

    void erase_if(const Entry::pred_fun& p)
    {
        NOT_IMPLEMENTED;
    }

    void erase_if(const Entry::range& r, const Entry::pred_fun& p)
    {
        NOT_IMPLEMENTED;
    }

    // as vector
    Entry::iterator at(int idx)
    {
        try
        {
            auto& m = std::get<Entry::Type::Array>(m_data_);
            return Entry::iterator(&m[idx]);
        }
        catch (std::bad_variant_access&)
        {
            return Entry::iterator();
        };
    }

    Entry::iterator push_back()
    {
        if (type() == Entry::Type::Null)
        {
            m_data_.emplace<Entry::Type::Array>();
        }
        try
        {
            auto& m = std::get<Entry::Type::Array>(m_data_);
            m.emplace_back(Entry(m_self_));
            return Entry::iterator(&*m.rbegin());
        }
        catch (std::bad_variant_access&)
        {
            return Entry::iterator();
        };
    }

    Entry pop_back()
    {
        try
        {
            auto& m = std::get<Entry::Type::Array>(m_data_);
            Entry res;
            m.rbegin()->swap(res);
            m.pop_back();
            return std::move(res);
        }
        catch (std::bad_variant_access&)
        {
            return Entry();
        }
    }

    // as object
    Entry::const_iterator find(const std::string& key) const
    {
        try
        {
            auto const& m = std::get<Entry::Type::Object>(m_data_);
            auto it = m.find(key);
            if (it != m.end())
            {
                return it->second.self();
            }
        }
        catch (std::bad_variant_access&)
        {
        }
        return Entry::const_iterator();
    }

    Entry::iterator find(const std::string& key)
    {
        try
        {
            auto const& m = std::get<Entry::Type::Object>(m_data_);
            auto it = m.find(key);
            if (it != m.end())
            {
                return const_cast<Entry&>(it->second).self();
            }
        }
        catch (std::bad_variant_access&)
        {
        }
        return Entry::iterator();
    }

    Entry::iterator insert(const std::string& key)
    {
        if (type() == Entry::Type::Null)
        {
            m_data_.emplace<Entry::Type::Object>();
        }
        try
        {
            auto& m = std::get<Entry::Type::Object>(m_data_);

            return Entry::iterator(&(m.emplace(key, Entry(m_self_)).first->second));
        }
        catch (std::bad_variant_access&)
        {
            return Entry::iterator();
        }
    }

    Entry erase(const std::string& key)
    {
        try
        {
            auto& m = std::get<Entry::Type::Object>(m_data_);
            auto it = m.find(key);
            if (it != m.end())
            {
                Entry res;
                res.swap(it->second);
                m.erase(it);
                return std::move(res);
            }
        }
        catch (std::bad_variant_access&)
        {
        }
        return Entry();
    }
};

Entry::Entry(Entry* parent) : m_pimpl_(new EntryInterfaceInMemory(this, parent)) {}

Entry::Entry(const this_type& other) : m_pimpl_(other.m_pimpl_->copy()) {}

Entry::Entry(this_type&& other) : m_pimpl_(other.m_pimpl_.release()) {}

Entry::~Entry() {}

void Entry::swap(this_type& other) { std::swap(m_pimpl_, other.m_pimpl_); }

Entry& Entry::operator=(this_type const& other)
{
    this_type(other).swap(*this);
    return *this;
}

//
std::string Entry::prefix() const { return m_pimpl_->prefix(); }

// metadata
Entry::Type Entry::type() const { return m_pimpl_->type(); }
bool Entry::is_null() const { return type() == Type::Null; }
bool Entry::is_single() const { return type() == Type::Single; }
bool Entry::is_tensor() const { return type() == Type::Tensor; }
bool Entry::is_block() const { return type() == Type::Block; }
bool Entry::is_array() const { return type() == Type::Array; }
bool Entry::is_object() const { return type() == Type::Object; }

bool Entry::is_root() const { return !parent(); }
bool Entry::is_leaf() const { return type() < Type::Array; };

// attributes
bool Entry::has_attribute(const std::string& name) const { return m_pimpl_->has_attribute(name); }

const Entry::single_t Entry::get_attribute_raw(const std::string& name) { return m_pimpl_->get_attribute_raw(name); }

void Entry::set_attribute_raw(const std::string& name, const single_t& value) { m_pimpl_->set_attribute_raw(name, value); }

void Entry::remove_attribute(const std::string& name) { m_pimpl_->remove_attribute(name); }

std::map<std::string, Entry::single_t> Entry::attributes() const { return m_pimpl_->attributes(); }

// as leaf
void Entry::set_single(const single_t& v) { m_pimpl_->set_single(v); }

Entry::single_t Entry::get_single() const { return m_pimpl_->get_single(); }

void Entry::set_tensor(const tensor_t& v) { m_pimpl_->set_tensor(v); }

Entry::tensor_t Entry::get_tensor() const { return m_pimpl_->get_tensor(); }

void Entry::set_block(const block_t& v) { m_pimpl_->set_block(v); }

Entry::block_t Entry::get_block() const { return m_pimpl_->get_block(); }

// as Tree
Entry::iterator Entry::parent() const { return m_pimpl_->parent(); }

Entry::const_iterator Entry::self() const { return const_iterator(this); }

Entry::iterator Entry::self() { return iterator(this); }

Entry::iterator Entry::next() const { return m_pimpl_->next(); }

Entry::iterator Entry::first_child() const { return m_pimpl_->first_child(); }

Entry::iterator Entry::last_child() const { return m_pimpl_->last_child(); }

Entry::range Entry::children() const { return range{first_child(), last_child()}; }

// as container
size_t Entry::size() const { return m_pimpl_->size(); }

Entry::range Entry::find(const pred_fun& pred) { return m_pimpl_->find(pred); }

void Entry::erase(const iterator& p) { m_pimpl_->erase(p); }

void Entry::erase_if(const pred_fun& p) { m_pimpl_->erase_if(p); }

void Entry::erase_if(const range& r, const pred_fun& p) { m_pimpl_->erase_if(r, p); }

// as vector
Entry::iterator Entry::at(int idx) { return m_pimpl_->at(idx); }

Entry::iterator Entry::push_back() { return m_pimpl_->push_back(); }

Entry::iterator Entry::push_back(const Entry& other)
{
    auto p = push_back();
    Entry(other).swap(*p);
    return p;
}

Entry::iterator Entry::push_back(Entry&& other)
{
    auto p = push_back();
    p->swap(other);
    return p;
}

Entry Entry::pop_back() { NOT_IMPLEMENTED; }

Entry& Entry::operator[](int idx)
{
    if (idx < 0)
    {
        return *push_back();
    }
    else
    {
        auto p = at(idx);
        if (!p)
        {
            throw std::out_of_range("index out of range");
        }
        return *p;
    }
}

// as map
// @note : map is unordered
bool Entry::has_a(const std::string& key) { return !find(key); }

Entry::iterator Entry::find(const std::string& key) { return m_pimpl_->find(key); }

Entry::iterator Entry::at(const std::string& key)
{
    auto p = find(key);
    if (!p)
    {
        throw std::out_of_range(key);
    }
    return p;
}

Entry& Entry::operator[](const std::string& key) { return *insert(key); }

Entry::iterator Entry::insert(const std::string& key) { return m_pimpl_->insert(key); }

Entry::iterator Entry::insert(const std::string& key, const Entry& other)
{
    auto p = insert(key);
    Entry(other).swap(*p);
    return p;
}

Entry::iterator Entry::insert(const std::string& key, Entry&& other)
{
    auto p = insert(key);
    p->swap(other);
    return p;
}

Entry Entry::erase(const std::string& key) { return m_pimpl_->erase(key); }

//-------------------------------------------------------------------
// level 2
size_t Entry::depth() const
{
    auto p = parent();
    return p == nullptr ? 0 : p->depth() + 1;
}

size_t Entry::height() const
{
    NOT_IMPLEMENTED;
    return 0;
}

Entry::range Entry::slibings() const { return range{next(), const_cast<this_type*>(this)->self()}; } // return slibings

Entry::range Entry::ancestor() const
{
    NOT_IMPLEMENTED;
    return range{};
}

Entry::range Entry::descendants() const
{
    NOT_IMPLEMENTED;
    return range{};
}

Entry::range Entry::leaves() const
{
    NOT_IMPLEMENTED;
    return range{};
}

Entry::range Entry::shortest_path(iterator const& target) const
{
    NOT_IMPLEMENTED;
    return range{};
}

ptrdiff_t Entry::distance(const this_type& target) const
{
    NOT_IMPLEMENTED;
    return 0;
}

Entry load(const std::string& uri) { NOT_IMPLEMENTED; }

void save(const Entry&, const std::string& uri) { NOT_IMPLEMENTED; }

Entry load(const std::istream&, const std::string& format) { NOT_IMPLEMENTED; }

void save(const Entry&, const std::ostream&, const std::string& format) { NOT_IMPLEMENTED; }

} // namespace sp